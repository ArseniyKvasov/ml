import json
import os
import tempfile
import uuid
from typing import Any, Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.config import WHISPER_MODEL_SIZE
from app.services.transcriber_service import stream_transcription

router = APIRouter(prefix="/transcriber", tags=["transcriber"])


def error_payload(code: str, message: str) -> dict[str, str]:
    return {"type": "error", "code": code, "message": message}


@router.get("/health")
async def health() -> dict[str, Any]:
    return {"status": "healthy", "model": WHISPER_MODEL_SIZE, "auto_language": True}


@router.websocket("/ws/transcribe")
async def websocket_transcribe(websocket: WebSocket) -> None:
    await websocket.accept()

    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".audio")
    temp_path = temp_file.name
    total_audio_bytes = 0

    try:
        init_message = await websocket.receive()
        init_text = init_message.get("text")
        if not init_text:
            await websocket.send_json(error_payload("INVALID_INIT", "First message must be JSON init"))
            await websocket.close(code=1003)
            return

        init_data = _parse_json(init_text)
        if not init_data or init_data.get("type") != "init":
            await websocket.send_json(error_payload("INVALID_INIT", "Expected init command"))
            await websocket.close(code=1003)
            return

        config = init_data.get("config") if isinstance(init_data.get("config"), dict) else {}
        language = _normalize_language(config.get("language"))

        await websocket.send_json(
            {
                "type": "init_ack",
                "status": "ready",
                "session_id": str(uuid.uuid4()),
            }
        )

        should_transcribe = False

        while True:
            message = await websocket.receive()

            if message.get("type") == "websocket.disconnect":
                return

            binary_data = message.get("bytes")
            text_data = message.get("text")

            if binary_data is not None:
                temp_file.write(binary_data)
                total_audio_bytes += len(binary_data)
                continue

            if text_data is None:
                continue

            payload = _parse_json(text_data)
            if not payload:
                continue

            msg_type = payload.get("type")
            if msg_type == "ping":
                await websocket.send_json({"type": "pong"})
            elif msg_type == "cancel":
                await websocket.send_json({"type": "cancel_ack", "status": "cancelled"})
                await websocket.close(code=1000)
                return
            elif msg_type == "end":
                should_transcribe = True
                break

        if not should_transcribe:
            return

        temp_file.flush()
        temp_file.close()

        if total_audio_bytes == 0:
            await websocket.send_json(error_payload("NO_AUDIO", "Audio stream is empty"))
            await websocket.close(code=1000)
            return

        async for item in stream_transcription(temp_path, language):
            item_type = item.get("type")

            if item_type == "language_info":
                await websocket.send_json(item)
            elif item_type == "transcript":
                await websocket.send_json(item)
            elif item_type == "error":
                await websocket.send_json(item)
                await websocket.close(code=1011)
                return
            elif item_type == "done":
                await websocket.close(code=1000)
                return

    except WebSocketDisconnect:
        return
    except Exception as exc:
        try:
            await websocket.send_json(error_payload("WHISPER_ERROR", str(exc)))
            await websocket.close(code=1011)
        except Exception:
            pass
    finally:
        try:
            temp_file.close()
        except Exception:
            pass
        if os.path.exists(temp_path):
            os.remove(temp_path)


def _parse_json(text: str) -> Optional[dict[str, Any]]:
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return None
    return data if isinstance(data, dict) else None


def _normalize_language(value: Any) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None
