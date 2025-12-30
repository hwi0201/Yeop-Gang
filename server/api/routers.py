from fastapi import APIRouter, BackgroundTasks, Depends, UploadFile
from fastapi.params import Form, File
from sqlmodel import Session, select

from ai.pipelines.rag import RAGPipeline
from api.schemas import (
    ChatResponse,
    QueryRequest,
    StatusResponse,
    UploadResponse,
)
from core.db import get_session
from core.models import Course, CourseStatus, Instructor
from core.storage import save_course_assets
from core.tasks import enqueue_processing_task
from ai.config import AISettings

router = APIRouter(prefix="", tags=["api"])


def get_pipeline(settings: AISettings = Depends(AISettings)) -> RAGPipeline:
    return RAGPipeline(settings)


@router.get("/health")
def health_check() -> dict:
    return {"status": "ok", "service": "Yeop-Gang"}


@router.post("/upload", response_model=UploadResponse)
async def upload_course_assets(
    background_tasks: BackgroundTasks,
    instructor_id: str = Form(...),
    course_id: str = Form(...),
    video: UploadFile | None = File(None),
    pdf: UploadFile | None = File(None),
    session: Session = Depends(get_session),
) -> UploadResponse:
    # Ensure instructor/course exist
    instructor = session.get(Instructor, instructor_id)
    if not instructor:
        instructor = Instructor(id=instructor_id)
        session.add(instructor)

    course = session.get(Course, course_id)
    if not course:
        course = Course(id=course_id, instructor_id=instructor_id)
        session.add(course)
    course.status = CourseStatus.processing
    session.commit()

    paths = save_course_assets(
        instructor_id=instructor_id,
        course_id=course_id,
        video=video,
        pdf=pdf,
    )

    enqueue_processing_task(
        background_tasks,
        course_id=course_id,
        instructor_id=instructor_id,
        video_path=paths.get("video"),
        pdf_path=paths.get("pdf"),
    )
    return UploadResponse(
        course_id=course_id,
        instructor_id=instructor_id,
        status=course.status.value,
    )


@router.get("/status/{course_id}", response_model=StatusResponse)
def status(course_id: str, session: Session = Depends(get_session)) -> StatusResponse:
    course = session.get(Course, course_id)
    if not course:
        return StatusResponse(course_id=course_id, status="not_found", progress=0)

    progress = 0 if course.status == CourseStatus.processing else 100
    return StatusResponse(
        course_id=course_id,
        status=course.status.value,
        progress=progress,
        message=None,
    )


@router.post("/chat/ask", response_model=ChatResponse)
def ask(
    payload: QueryRequest,
    pipeline: RAGPipeline = Depends(get_pipeline),
) -> ChatResponse:
    result = pipeline.query(payload.question, course_id=payload.course_id)
    return ChatResponse(
        answer=result.get("answer", ""),
        sources=[str(src) for src in result.get("documents", [])],
        conversation_id=payload.conversation_id or "demo",
        course_id=payload.course_id,
    )

