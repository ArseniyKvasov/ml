from fastapi import FastAPI

from app.api.summary import router as summary_router
from app.api.test_generator import router as test_router
from app.api.transcriber import router as transcriber_router

app = FastAPI(title="Lecture ML Service", version="1.0.0")

app.include_router(transcriber_router)
app.include_router(summary_router)
app.include_router(test_router)


@app.get("/")
async def root() -> dict[str, str]:
    return {"status": "ok"}
