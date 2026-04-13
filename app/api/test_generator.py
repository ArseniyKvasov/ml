from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.config import TEST_LLM_MODEL
from app.schemas import TestRequest, TestSuccessResponse
from app.services.llm_service import LLMService, LLMServiceError, parse_json_array

router = APIRouter(prefix="/test", tags=["test"])
llm_service = LLMService()


@router.get("/health")
async def health() -> dict[str, object]:
    return {"status": "healthy", "llm_available": await llm_service.healthcheck()}


@router.post("/generate", response_model=TestSuccessResponse)
async def generate_test(payload: TestRequest):
    if not payload.summary:
        return JSONResponse(
            status_code=400,
            content={
                "status": "error",
                "code": "INVALID_INPUT",
                "message": "Summary is empty",
            },
        )

    summary_chunks = []
    for item in payload.summary:
        subtopic = item.subtopic.strip()
        content = item.content.strip()
        if not subtopic and not content:
            continue
        summary_chunks.append(f"Подтема: {subtopic}\nСодержание: {content}")

    summary_text = "\n\n".join(summary_chunks).strip()
    if not summary_text:
        return JSONResponse(
            status_code=400,
            content={
                "status": "error",
                "code": "INVALID_INPUT",
                "message": "Summary is empty",
            },
        )

    prompt = f"""Ты — эксперт по созданию тестов для проверки знаний на основе лекции.

На основе конспекта лекции создай тест из {payload.num_questions} вопросов.

Правила:
1. Вопросы должны покрывать ключевые темы лекции
2. Типы вопросов: multiple_choice (70%) и open_ended (30%)
3. Для multiple_choice: 4 варианта ответа, только один правильный
4. Для open_ended: правильный ответ — развернутое объяснение (2-3 предложения)
5. Если в лекции есть формулы — используй LaTeX: \\( E = mc^2 \\)
6. Добавь пояснение (explanation) к каждому вопросу
7. Добавь subtopic — к какой теме лекции относится вопрос.

Формат ответа ТОЛЬКО JSON массив:
[
  {{
    "question_id": 1,
    "question_text": "текст вопроса",
    "question_type": "multiple_choice",
    "options": ["вариант 1", "вариант 2", "вариант 3", "вариант 4"],
    "correct_answer": 0,
    "explanation": "пояснение",
    "subtopic": "тема"
  }}
]

Для open_ended поле options = null, correct_answer = "развернутый ответ"

Конспект лекции:
{summary_text}
"""

    try:
        llm_raw = await llm_service.generate(prompt, model=TEST_LLM_MODEL)
        test_items = parse_json_array(llm_raw)
    except LLMServiceError as exc:
        status_code = 504 if exc.code == "TIMEOUT" else 502
        return JSONResponse(
            status_code=status_code,
            content={"status": "error", "code": exc.code, "message": exc.message},
        )

    required = {
        "question_id",
        "question_text",
        "question_type",
        "options",
        "correct_answer",
        "explanation",
        "subtopic",
    }

    validated = []
    for item in test_items:
        if not isinstance(item, dict) or not required.issubset(item.keys()):
            return JSONResponse(
                status_code=400,
                content={
                    "status": "error",
                    "code": "INVALID_INPUT",
                    "message": "Invalid test JSON structure",
                },
            )

        question_type = item["question_type"]
        if question_type not in {"multiple_choice", "open_ended"}:
            return JSONResponse(
                status_code=400,
                content={
                    "status": "error",
                    "code": "INVALID_INPUT",
                    "message": "question_type must be multiple_choice or open_ended",
                },
            )

        validated.append(item)

    return {"status": "success", "test": validated}
