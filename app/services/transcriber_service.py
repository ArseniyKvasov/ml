import asyncio
import threading
from functools import lru_cache
from typing import Any, Optional

from faster_whisper import WhisperModel

from app.config import WHISPER_COMPUTE_TYPE, WHISPER_DEVICE, WHISPER_MODEL_SIZE


@lru_cache(maxsize=1)
def get_whisper_model() -> WhisperModel:
    return WhisperModel(
        WHISPER_MODEL_SIZE,
        device=WHISPER_DEVICE,
        compute_type=WHISPER_COMPUTE_TYPE,
    )


async def stream_transcription(audio_path: str, language: Optional[str]):
    queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
    loop = asyncio.get_running_loop()

    def push(item: dict[str, Any]) -> None:
        loop.call_soon_threadsafe(queue.put_nowait, item)

    def worker() -> None:
        try:
            model = get_whisper_model()
            segments, info = model.transcribe(audio_path, language=language)

            push(
                {
                    "type": "language_info",
                    "detected_language": info.language,
                    "confidence": round(float(info.language_probability), 4),
                }
            )

            for segment in segments:
                push(
                    {
                        "type": "transcript",
                        "start_ms": int(segment.start * 1000),
                        "end_ms": int(segment.end * 1000),
                        "text": segment.text.strip(),
                        "is_final": True,
                    }
                )

            push({"type": "done"})
        except Exception as exc:
            push(
                {
                    "type": "error",
                    "code": "WHISPER_ERROR",
                    "message": str(exc),
                }
            )

    thread = threading.Thread(target=worker, daemon=True)
    thread.start()

    while True:
        item = await queue.get()
        yield item

        if item.get("type") in {"done", "error"}:
            break
