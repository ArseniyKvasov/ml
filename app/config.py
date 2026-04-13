import os


def _parse_models(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


WHISPER_MODEL_SIZE = os.getenv("WHISPER_MODEL_SIZE", "small")
WHISPER_DEVICE = os.getenv("WHISPER_DEVICE", "cpu")
WHISPER_COMPUTE_TYPE = os.getenv("WHISPER_COMPUTE_TYPE", "int8")

LLM_API_URL = os.getenv("LLM_API_URL", "http://91.103.253.236/generate")
LLM_API_KEY = os.getenv("LLM_API_KEY", "QbxxPuE5IVbNvvUFggsw37MFVyMHgM8p")
SUMMARY_LLM_MODEL = os.getenv("SUMMARY_LLM_MODEL", "meta-llama/llama-4-scout-17b-16e-instruct")
TEST_LLM_MODEL = os.getenv("TEST_LLM_MODEL", "llama-3.3-70b-versatile")
SUMMARY_MODEL_CANDIDATES = _parse_models(
    os.getenv(
        "SUMMARY_MODEL_CANDIDATES",
        f"{SUMMARY_LLM_MODEL},llama-3.1-8b-instant,qwen/qwen3-32b",
    )
)
TEST_MODEL_CANDIDATES = _parse_models(
    os.getenv(
        "TEST_MODEL_CANDIDATES",
        f"{TEST_LLM_MODEL},llama-3.1-8b-instant,qwen/qwen3-32b",
    )
)
MODEL_FALLBACK_ATTEMPTS = int(os.getenv("MODEL_FALLBACK_ATTEMPTS", "3"))
LLM_TIMEOUT_SECONDS = float(os.getenv("LLM_TIMEOUT_SECONDS", "60"))
LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.3"))
LLM_MAX_TOKENS = int(os.getenv("LLM_MAX_TOKENS", "5000"))
LLM_MAX_RETRIES = int(os.getenv("LLM_MAX_RETRIES", "3"))
LLM_RETRY_BACKOFF_SECONDS = float(os.getenv("LLM_RETRY_BACKOFF_SECONDS", "0.7"))
LLM_HEALTH_TTL_SECONDS = int(os.getenv("LLM_HEALTH_TTL_SECONDS", "30"))
