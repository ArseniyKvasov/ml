import logging

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.config import MODEL_FALLBACK_ATTEMPTS, SUMMARY_MODEL_CANDIDATES
from app.schemas import SummaryRequest, SummarySuccessResponse
from app.services.llm_service import LLMService, LLMServiceError, parse_json_array

router = APIRouter(prefix="/summary", tags=["summary"])
llm_service = LLMService()
logger = logging.getLogger("app")


@router.get("/health")
async def health() -> dict[str, object]:
    return {"status": "healthy", "llm_available": await llm_service.healthcheck()}


@router.post("/summarize", response_model=SummarySuccessResponse)
async def summarize(payload: SummaryRequest):
    transcript_text = "\n".join(segment.text.strip() for segment in payload.transcript if segment.text.strip())
    if not transcript_text:
        return JSONResponse(
            status_code=400,
            content={
                "status": "error",
                "code": "INVALID_INPUT",
                "message": "Transcript is empty",
            },
        )

    prompt = f"""Ты — ассистент, который составляет структурированный конспект лекции.

Правила:
1. Разбей конспект на логические подтемы (от 3 до 10)
2. Каждая подтема должна иметь заголовок (subtopic) и содержание (content)
3. Если в тексте есть математические формулы или физические выражения — используй LaTeX: \\( E = mc^2 \\) или \\[ \\int x^2 dx \\]
4. Конспект должен быть кратким, но информативным
5. Верни только валидный JSON-массив объектов и ничего больше
6. Не используй markdown, кодовые блоки, комментарии, префиксы или пояснения
7. Каждый объект обязан содержать строки subtopic и content
8. JSON должен начинаться с символа [ и заканчиваться символом ]

Требуемый формат ответа (строго):
[{{"subtopic":"...","content":"..."}},{{"subtopic":"...","content":"..."}}]

Транскрипт лекции:
{transcript_text}
"""

    attempts = min(max(1, MODEL_FALLBACK_ATTEMPTS), max(1, len(SUMMARY_MODEL_CANDIDATES)))
    last_error_code = "LLM_UNAVAILABLE"
    last_error_message = "Failed to generate summary with fallback models"
    last_status_code = 502

    for idx in range(attempts):
        model = SUMMARY_MODEL_CANDIDATES[idx]
        llm_raw = ""
        try:
            llm_raw = await llm_service.generate(prompt, model=model)
            summary_items = parse_json_array(llm_raw)
        except LLMServiceError as exc:
            logger.warning(
                "Summary generation failed attempt=%s/%s model=%s code=%s error=%s raw_preview=%s",
                idx + 1,
                attempts,
                model,
                exc.code,
                exc.message,
                llm_raw[:600],
            )
            last_error_code = exc.code
            last_error_message = exc.message
            last_status_code = 504 if exc.code == "TIMEOUT" else 502
            continue

        validated = []
        valid = True
        for item in summary_items:
            if not isinstance(item, dict) or "subtopic" not in item or "content" not in item:
                logger.warning(
                    "Summary validation failed attempt=%s/%s model=%s item=%s raw_preview=%s",
                    idx + 1,
                    attempts,
                    model,
                    str(item)[:400],
                    llm_raw[:600],
                )
                valid = False
                last_error_code = "INVALID_INPUT"
                last_error_message = "Invalid summary JSON structure"
                last_status_code = 502
                break
            validated.append(
                {
                    "subtopic": str(item["subtopic"]).strip(),
                    "content": str(item["content"]).strip(),
                }
            )

        if valid:
            logger.info(
                "Summary generation success attempt=%s/%s model=%s items=%s",
                idx + 1,
                attempts,
                model,
                len(validated),
            )
            return {"status": "success", "summary": validated}

    return JSONResponse(
        status_code=last_status_code,
        content={"status": "error", "code": last_error_code, "message": last_error_message},
    )
