from typing import List, Literal, Optional, Union

from pydantic import BaseModel, Field, conint


class TranscriptSegment(BaseModel):
    start_ms: int = Field(ge=0)
    text: str


class SummaryRequest(BaseModel):
    transcript: List[TranscriptSegment]


class SummaryItem(BaseModel):
    subtopic: str
    content: str


class SummarySuccessResponse(BaseModel):
    status: Literal["success"]
    summary: List[SummaryItem]


class ErrorResponse(BaseModel):
    status: Literal["error"]
    code: str
    message: str


class TestRequest(BaseModel):
    transcript: List[TranscriptSegment]
    num_questions: conint(ge=1, le=50) = 10


class TestQuestion(BaseModel):
    question_id: int
    question_text: str
    question_type: Literal["multiple_choice", "open_ended"]
    options: Optional[List[str]]
    correct_answer: Union[int, str]
    explanation: str
    subtopic: str


class TestSuccessResponse(BaseModel):
    status: Literal["success"]
    test: List[TestQuestion]
