import os

WHISPER_MODEL_SIZE = os.getenv("WHISPER_MODEL_SIZE", "small")
WHISPER_DEVICE = os.getenv("WHISPER_DEVICE", "cpu")
WHISPER_COMPUTE_TYPE = os.getenv("WHISPER_COMPUTE_TYPE", "int8")

LLM_API_URL = os.getenv("LLM_API_URL", "http://91.103.253.236/generate")
LLM_API_KEY = os.getenv("LLM_API_KEY", "QbxxPuE5IVbNvvUFggsw37MFVyMHgM8p")
LLM_MODEL = os.getenv("LLM_MODEL", "llama-3.1-8b-instant")
LLM_TIMEOUT_SECONDS = float(os.getenv("LLM_TIMEOUT_SECONDS", "60"))
