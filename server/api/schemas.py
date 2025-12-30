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

