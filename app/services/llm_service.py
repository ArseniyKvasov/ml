import json
import re
from typing import Any

import httpx

from app.config import LLM_API_KEY, LLM_API_URL, LLM_MODEL, LLM_TIMEOUT_SECONDS


class LLMServiceError(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


class LLMService:
    def __init__(self) -> None:
        self.api_url = LLM_API_URL
        self.api_key = LLM_API_KEY
        self.model = LLM_MODEL
        self.timeout = LLM_TIMEOUT_SECONDS

    async def generate(self, prompt: str) -> str:
        headers = {"X-API-Key": self.api_key}
        payload = {
            "model": self.model,
            "prompt": prompt,
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(self.api_url, headers=headers, json=payload)
                response.raise_for_status()
        except httpx.TimeoutException as exc:
            raise LLMServiceError("TIMEOUT", "LLM API timeout") from exc
        except httpx.HTTPError as exc:
            raise LLMServiceError("LLM_UNAVAILABLE", f"LLM API error: {exc}") from exc

        data = response.json()
        text = _extract_text_from_llm_response(data)
        if not text.strip():
            raise LLMServiceError("LLM_UNAVAILABLE", "Empty LLM response")
        return text

    async def healthcheck(self) -> bool:
        try:
            headers = {"X-API-Key": self.api_key}
            payload = {
                "model": self.model,
                "prompt": 'Return valid JSON array: [{"subtopic":"ok","content":"ok"}]',
            }
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.post(self.api_url, headers=headers, json=payload)
                response.raise_for_status()
            return True
        except Exception:
            return False


def _extract_text_from_llm_response(data: Any) -> str:
    if isinstance(data, str):
        return data

    if isinstance(data, dict):
        for key in ("response", "text", "result", "output", "generated_text", "content"):
            value = data.get(key)
            if isinstance(value, str):
                return value

        choices = data.get("choices")
        if isinstance(choices, list) and choices:
            first = choices[0]
            if isinstance(first, dict):
                if isinstance(first.get("text"), str):
                    return first["text"]
                message = first.get("message")
                if isinstance(message, dict) and isinstance(message.get("content"), str):
                    return message["content"]

        return json.dumps(data, ensure_ascii=False)

    if isinstance(data, list):
        return json.dumps(data, ensure_ascii=False)

    return str(data)


def parse_json_array(raw_text: str) -> list[dict[str, Any]]:
    text = raw_text.strip()

    # Drop markdown fences if present.
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?", "", text).strip()
        if text.endswith("```"):
            text = text[:-3].strip()

    parsed_direct = _try_parse_json(text)
    if isinstance(parsed_direct, list):
        return parsed_direct

    match = re.search(r"\[.*\]", text, flags=re.DOTALL)
    if not match:
        raise LLMServiceError("INVALID_INPUT", "LLM response is not a JSON array")

    parsed = _try_parse_json(match.group(0))
    if not isinstance(parsed, list):
        raise LLMServiceError("INVALID_INPUT", "LLM response array parse failed")
    return parsed


def _try_parse_json(value: str) -> Any:
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return None
