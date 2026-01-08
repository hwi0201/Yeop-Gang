from typing import Literal, Optional

from pydantic import BaseModel, Field, HttpUrl


class IngestRequest(BaseModel):
    course_id: str = Field(..., description="코스 식별자")
    instructor_id: Optional[str] = None
    source_url: Optional[HttpUrl] = None
    text: Optional[str] = None


class QueryRequest(BaseModel):
    course_id: str
    question: str
    conversation_id: Optional[str] = None
    current_time: Optional[float] = None  # 현재 비디오 재생 시간 (초)


class ChatMessage(BaseModel):
    role: Literal["user", "assistant", "system"]
    content: str
    timestamp: Optional[str] = None


class ChatResponse(BaseModel):
    answer: str
    sources: list[str] = []
    conversation_id: Optional[str] = None
    course_id: Optional[str] = None


class UploadResponse(BaseModel):
    course_id: str
    instructor_id: str
    status: str


class StatusResponse(BaseModel):
    course_id: str
    status: str
    progress: int = 0
    message: Optional[str] = None


class SummaryRequest(BaseModel):
    course_id: str


class SummaryResponse(BaseModel):
    course_id: str
    summary: str
    key_points: list[str] = []


class QuizRequest(BaseModel):
    course_id: str
    num_questions: int = 5


class QuizQuestion(BaseModel):
    id: int
    question: str
    options: list[str]
    correct_answer: int  # 0-based index
    explanation: Optional[str] = None


class QuizResponse(BaseModel):
    course_id: str
    questions: list[QuizQuestion]
    quiz_id: Optional[str] = None


class QuizSubmitRequest(BaseModel):
    course_id: str
    quiz_id: Optional[str] = None
    answers: dict[int, int]  # question_id -> selected_option_index
    questions: Optional[list] = None  # 퀴즈 문제 데이터 (채점용)


class QuizResult(BaseModel):
    course_id: str
    score: int
    total: int
    percentage: float
    correct_answers: list[int]
    wrong_answers: list[int]
