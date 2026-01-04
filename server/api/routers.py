from fastapi import APIRouter, BackgroundTasks, Depends, UploadFile
from fastapi.params import Form, File
from fastapi.responses import FileResponse
from sqlmodel import Session, select
from pathlib import Path

from ai.pipelines.rag import RAGPipeline
from api.schemas import (
    ChatResponse,
    QueryRequest,
    StatusResponse,
    UploadResponse,
)
from core.db import get_session
from core.models import Course, CourseStatus, Instructor, Video
from core.storage import save_course_assets
from core.tasks import enqueue_processing_task
from ai.config import AISettings

router = APIRouter(prefix="", tags=["api"])

PROJECT_ROOT = Path(__file__).resolve().parents[2]


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


# 간단한 메모리 기반 대화 히스토리 저장소 (프로덕션에서는 DB 사용 권장)
_conversation_history: dict[str, list[dict[str, str]]] = {}


@router.get("/video/{course_id}")
def get_video(course_id: str, session: Session = Depends(get_session)) -> FileResponse:
    """
    Get video file for a course. Returns the first video file found for the course.
    For testing: can also serve files from ref/video/ folder.
    """
    # Try to get video from database (only video files with .mp4 extension)
    course = session.get(Course, course_id)
    if course:
        videos = session.exec(
            select(Video).where(
                Video.course_id == course_id,
                Video.filetype == "video"
            )
        ).all()
        for vid in videos:
            video_path = Path(vid.storage_path)
            # Only return files that exist and are .mp4 files (not .mp3 audio)
            if video_path.exists() and video_path.suffix.lower() == ".mp4":
                return FileResponse(video_path, media_type="video/mp4")
    
    # Fallback: try ref/video folder for testing
    ref_video = PROJECT_ROOT / "ref" / "video" / "testvedio_1.mp4"
    if ref_video.exists():
        return FileResponse(ref_video, media_type="video/mp4")
    
    from fastapi import HTTPException
    raise HTTPException(status_code=404, detail="Video not found")


@router.post("/chat/ask", response_model=ChatResponse)
def ask(
    payload: QueryRequest,
    pipeline: RAGPipeline = Depends(get_pipeline),
) -> ChatResponse:
    conversation_id = payload.conversation_id or "default"
    
    # 대화 히스토리 가져오기
    history = _conversation_history.get(conversation_id, [])
    
    # RAG 쿼리 실행
    result = pipeline.query(
        payload.question, 
        course_id=payload.course_id,
        conversation_history=history
    )
    
    answer = result.get("answer", "")
    
    # 대화 히스토리에 현재 질문과 답변 추가
    history.append({"role": "user", "content": payload.question})
    history.append({"role": "assistant", "content": answer})
    # 최대 20개 대화만 유지 (메모리 절약)
    if len(history) > 20:
        history = history[-20:]
    _conversation_history[conversation_id] = history
    
    return ChatResponse(
        answer=answer,
        sources=[str(src) for src in result.get("documents", [])],
        conversation_id=conversation_id,
        course_id=payload.course_id,
    )

