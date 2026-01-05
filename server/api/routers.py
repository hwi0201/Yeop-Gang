# dh: 이 파일은 기존 호환성을 위해 유지됩니다.
# dh: 새로운 보안 기능이 포함된 API는 server/api/dh_routers.py를 사용하세요.

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
    audio: UploadFile | None = File(None),
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
        audio=audio,
        pdf=pdf,
    )

    enqueue_processing_task(
        background_tasks,
        course_id=course_id,
        instructor_id=instructor_id,
        video_path=paths.get("video"),
        audio_path=paths.get("audio"),
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

    # 실제 진행도 필드 사용
    progress = getattr(course, 'progress', 0) if course.status == CourseStatus.processing else 100
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
    Get video/audio file for a course. Returns the first video or audio file found for the course.
    Supports both mp4 (video) and mp3 (audio) files.
    For testing: can also serve files from ref/video/ folder.
    """
    # Try to get video/audio from database
    course = session.get(Course, course_id)
    if course:
        # 우선 video 타입 파일 확인 (mp4 우선)
        videos = session.exec(
            select(Video).where(
                Video.course_id == course_id,
                Video.filetype == "video"
            )
        ).all()
        for vid in videos:
            video_path = Path(vid.storage_path)
            if video_path.exists():
                suffix = video_path.suffix.lower()
                if suffix == ".mp4":
                    return FileResponse(video_path, media_type="video/mp4")
                elif suffix in [".avi", ".mov", ".mkv", ".webm"]:
                    return FileResponse(video_path, media_type="video/mp4")  # 기본 비디오 타입
        
        # audio 타입 파일 확인 (mp3 포함)
        audios = session.exec(
            select(Video).where(
                Video.course_id == course_id,
                Video.filetype == "audio"
            )
        ).all()
        for audio in audios:
            audio_path = Path(audio.storage_path)
            if audio_path.exists():
                suffix = audio_path.suffix.lower()
                if suffix == ".mp3":
                    return FileResponse(audio_path, media_type="audio/mpeg")
                elif suffix == ".wav":
                    return FileResponse(audio_path, media_type="audio/wav")
                elif suffix in [".m4a", ".aac", ".ogg", ".flac"]:
                    return FileResponse(audio_path, media_type="audio/mpeg")
    
    # Fallback: try ref/video folder for testing
    ref_video = PROJECT_ROOT / "ref" / "video" / "testvedio_1.mp4"
    if ref_video.exists():
        return FileResponse(ref_video, media_type="video/mp4")
    
    from fastapi import HTTPException
    raise HTTPException(status_code=404, detail="Video/Audio not found")


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

