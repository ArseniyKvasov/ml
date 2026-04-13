from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.schemas import SummaryRequest, SummarySuccessResponse
from app.services.llm_service import LLMService, LLMServiceError, parse_json_array

router = APIRouter(prefix="/summary", tags=["summary"])
llm_service = LLMService()


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

Формат ответа ТОЛЬКО JSON:
[{{"subtopic": "...", "content": "..."}}, ...]

Транскрипт лекции:
{transcript_text}
"""

    try:
        llm_raw = await llm_service.generate(prompt)
        summary_items = parse_json_array(llm_raw)
    except LLMServiceError as exc:
        status_code = 504 if exc.code == "TIMEOUT" else 502
        return JSONResponse(
            status_code=status_code,
            content={"status": "error", "code": exc.code, "message": exc.message},
        )

    validated = []
    for item in summary_items:
        if not isinstance(item, dict) or "subtopic" not in item or "content" not in item:
            return JSONResponse(
                status_code=400,
                content={
                    "status": "error",
                    "code": "INVALID_INPUT",
                    "message": "Invalid summary JSON structure",
                },
            )
        validated.append(
            {
                "subtopic": str(item["subtopic"]).strip(),
                "content": str(item["content"]).strip(),
            }
        )

    return {"status": "success", "summary": validated}
