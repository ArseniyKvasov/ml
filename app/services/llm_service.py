import asyncio
import json
import re
import time
from typing import Any, Optional

import httpx

from app.config import (
    GROQ_API_KEY,
    GROQ_BASE_URL,
    LLM_HEALTH_TTL_SECONDS,
    LLM_MAX_RETRIES,
    LLM_RETRY_BACKOFF_SECONDS,
    LLM_MAX_TOKENS,
    LLM_MODEL,
    LLM_TEMPERATURE,
    LLM_TIMEOUT_SECONDS,
)


class LLMServiceError(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


class LLMService:
    _health_cache_value: bool = False
    _health_cache_until: float = 0.0
    _health_lock = asyncio.Lock()

    def __init__(self) -> None:
        self.base_url = GROQ_BASE_URL.rstrip("/")
        self.api_key = GROQ_API_KEY
        self.model = LLM_MODEL
        self.timeout = LLM_TIMEOUT_SECONDS
        self.temperature = LLM_TEMPERATURE
        self.max_tokens = LLM_MAX_TOKENS
        self.max_retries = LLM_MAX_RETRIES
        self.retry_backoff_seconds = LLM_RETRY_BACKOFF_SECONDS
        self.health_ttl_seconds = LLM_HEALTH_TTL_SECONDS

    async def generate(self, prompt: str) -> str:
        if not self.api_key:
            raise LLMServiceError("LLM_UNAVAILABLE", "GROQ_API_KEY is not set")

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
        }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            last_exc: Optional[Exception] = None
            for attempt in range(1, self.max_retries + 1):
                try:
                    response = await client.post(
                        f"{self.base_url}/chat/completions",
                        headers=headers,
                        json=payload,
                    )
                    response.raise_for_status()
                    data = response.json()
                    text = _extract_text_from_llm_response(data)
                    if not text.strip():
                        raise LLMServiceError("LLM_UNAVAILABLE", "Empty LLM response")
                    return text
                except httpx.TimeoutException as exc:
                    last_exc = exc
                    if attempt >= self.max_retries:
                        raise LLMServiceError("TIMEOUT", "LLM API timeout") from exc
                except httpx.HTTPStatusError as exc:
                    last_exc = exc
                    status_code = exc.response.status_code
                    # Retry only for transient statuses.
                    if status_code not in {429, 500, 502, 503, 504} or attempt >= self.max_retries:
                        raise LLMServiceError("LLM_UNAVAILABLE", f"LLM API returned {status_code}") from exc
                except httpx.HTTPError as exc:
                    last_exc = exc
                    if attempt >= self.max_retries:
                        raise LLMServiceError("LLM_UNAVAILABLE", f"LLM API error: {exc}") from exc

                await asyncio.sleep(self.retry_backoff_seconds * attempt)

            raise LLMServiceError("LLM_UNAVAILABLE", f"LLM request failed: {last_exc}")

    async def healthcheck(self) -> bool:
        if not self.api_key:
            return False

        now = time.monotonic()
        if now < self._health_cache_until:
            return self._health_cache_value

        async with self._health_lock:
            now = time.monotonic()
            if now < self._health_cache_until:
                return self._health_cache_value

            headers = {"Authorization": f"Bearer {self.api_key}"}

            ok = False
            try:
                async with httpx.AsyncClient(timeout=5.0) as client:
                    response = await client.get(f"{self.base_url}/models", headers=headers)
                    response.raise_for_status()
                ok = True
            except Exception:
                ok = False

            self._health_cache_value = ok
            self._health_cache_until = time.monotonic() + max(1, self.health_ttl_seconds)
            return ok


def _extract_text_from_llm_response(data: Any) -> str:
    if isinstance(data, str):
        return data

    if isinstance(data, dict):
        choices = data.get("choices")
        if isinstance(choices, list) and choices:
            first = choices[0]
            if isinstance(first, dict):
                message = first.get("message")
                if isinstance(message, dict) and isinstance(message.get("content"), str):
                    return message["content"]
                if isinstance(first.get("text"), str):
                    return first["text"]

        for key in ("response", "text", "result", "output", "generated_text", "content"):
            value = data.get(key)
            if isinstance(value, str):
                return value

        return json.dumps(data, ensure_ascii=False)

    if isinstance(data, list):
        return json.dumps(data, ensure_ascii=False)

    return str(data)


def parse_json_array(raw_text: str) -> list[dict[str, Any]]:
    text = raw_text.strip()

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
