"""
개선된 API 엔드포인트
- 강사/학생 분리
- 권한 체크
- 멀티 테넌트 데이터 격리
- 가드레일 적용
"""
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, UploadFile, status
from fastapi.params import Form, File
from fastapi.responses import FileResponse
from sqlmodel import Session, select
from pathlib import Path
from typing import Optional

from ai.pipelines.rag import RAGPipeline
from api.dh_schemas import (
    ChatResponse,
    QueryRequest,
    DetailedStatusResponse,
    UploadResponse,
    LoginRequest,
    TokenResponse,
    RegisterInstructorRequest,
    RegisterStudentRequest,
    EnrollCourseRequest,
    EnrollCourseResponse,
    SafeChatResponse,
)
from core.db import get_session
from core.dh_auth import (
    get_current_user,
    require_instructor,
    require_student,
    require_any_user,
    verify_course_access,
    create_access_token,
)
from core.dh_guardrails import apply_guardrails
from core.dh_models import Student, CourseEnrollment, EnrollmentStatus
from core.dh_tasks import enqueue_processing_task
from core.models import Course, CourseStatus, Instructor, Video
from core.storage import save_course_assets
from ai.config import AISettings

router = APIRouter(prefix="", tags=["api"])

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def get_pipeline(settings: AISettings = Depends(AISettings)) -> RAGPipeline:
    return RAGPipeline(settings)


# ==================== 인증 엔드포인트 ====================

@router.post("/auth/register/instructor", response_model=TokenResponse)
async def register_instructor(
    payload: RegisterInstructorRequest,
    session: Session = Depends(get_session),
) -> TokenResponse:
    """강사 등록"""
    # 기존 강사 확인
    existing = session.get(Instructor, payload.id)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Instructor already exists",
        )
    
    # 강사 생성
    instructor = Instructor(
        id=payload.id,
        name=payload.name,
        email=payload.email,
    )
    session.add(instructor)
    session.commit()
    
    # JWT 토큰 생성
    token = create_access_token(
        data={"sub": instructor.id, "role": "instructor"}
    )
    
    return TokenResponse(
        access_token=token,
        user_id=instructor.id,
        role="instructor",
    )


@router.post("/auth/register/student", response_model=TokenResponse)
async def register_student(
    payload: RegisterStudentRequest,
    session: Session = Depends(get_session),
) -> TokenResponse:
    """학생 등록"""
    # 기존 학생 확인
    existing = session.get(Student, payload.id)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Student already exists",
        )
    
    # 학생 생성
    student = Student(
        id=payload.id,
        name=payload.name,
        email=payload.email,
    )
    session.add(student)
    session.commit()
    
    # JWT 토큰 생성
    token = create_access_token(
        data={"sub": student.id, "role": "student"}
    )
    
    return TokenResponse(
        access_token=token,
        user_id=student.id,
        role="student",
    )


@router.post("/auth/login", response_model=TokenResponse)
async def login(
    payload: LoginRequest,
    session: Session = Depends(get_session),
) -> TokenResponse:
    """로그인 (간단한 구현 - 프로덕션에서는 비밀번호 검증 필요)"""
    if payload.role == "instructor":
        user = session.get(Instructor, payload.user_id)
    elif payload.role == "student":
        user = session.get(Student, payload.user_id)
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid role",
        )
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )
    
    # 실제로는 비밀번호 검증 필요
    # if not verify_password(payload.password, user.hashed_password):
    #     raise HTTPException(...)
    
    token = create_access_token(
        data={"sub": user.id, "role": payload.role}
    )
    
    return TokenResponse(
        access_token=token,
        user_id=user.id,
        role=payload.role,
    )


# ==================== 강사 전용 엔드포인트 ====================

@router.post("/instructor/upload", response_model=UploadResponse)
async def instructor_upload(
    background_tasks: BackgroundTasks,
    instructor_id: str = Form(...),
    course_id: str = Form(...),
    video: UploadFile | None = File(None),
    audio: UploadFile | None = File(None),
    pdf: UploadFile | None = File(None),
    current_user: dict = Depends(require_instructor),
    session: Session = Depends(get_session),
) -> UploadResponse:
    """강사용 파일 업로드 (권한 체크 포함) - 비디오와 오디오를 동시에 업로드 가능"""
    # 권한 확인: 자신의 강의만 업로드 가능
    if current_user["id"] != instructor_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only upload courses for yourself",
        )
    
    # Instructor/Course 확인
    instructor = session.get(Instructor, instructor_id)
    if not instructor:
        instructor = Instructor(id=instructor_id)
        session.add(instructor)
    
    course = session.get(Course, course_id)
    if not course:
        course = Course(id=course_id, instructor_id=instructor_id)
        session.add(course)
    elif course.instructor_id != instructor_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Course belongs to another instructor",
        )
    
    course.status = CourseStatus.processing
    session.commit()
    
    # 파일 저장
    paths = save_course_assets(
        instructor_id=instructor_id,
        course_id=course_id,
        video=video,
        audio=audio,
        pdf=pdf,
    )
    
    # 백그라운드 작업 등록 (백엔드 A processor 호출)
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


@router.get("/instructor/courses", response_model=list[dict])
async def instructor_courses(
    current_user: dict = Depends(require_instructor),
    session: Session = Depends(get_session),
) -> list[dict]:
    """강사의 강의 목록 조회 (자신의 강의만)"""
    courses = session.exec(
        select(Course).where(Course.instructor_id == current_user["id"])
    ).all()
    
    return [
        {
            "id": course.id,
            "title": course.title,
            "status": course.status.value,
            "created_at": course.created_at.isoformat(),
        }
        for course in courses
    ]


# ==================== 학생 전용 엔드포인트 ====================

@router.post("/student/enroll", response_model=EnrollCourseResponse)
async def enroll_course(
    payload: EnrollCourseRequest,
    current_user: dict = Depends(require_student),
    session: Session = Depends(get_session),
) -> EnrollCourseResponse:
    """강의 등록"""
    # 강의 존재 확인
    course = session.get(Course, payload.course_id)
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found",
        )
    
    # 이미 등록되어 있는지 확인
    existing = session.exec(
        select(CourseEnrollment).where(
            CourseEnrollment.student_id == current_user["id"],
            CourseEnrollment.course_id == payload.course_id,
        )
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Already enrolled in this course",
        )
    
    # 등록 생성
    enrollment = CourseEnrollment(
        student_id=current_user["id"],
        course_id=payload.course_id,
        status=EnrollmentStatus.active,
    )
    session.add(enrollment)
    session.commit()
    
    return EnrollCourseResponse(
        enrollment_id=enrollment.id or 0,
        student_id=enrollment.student_id,
        course_id=enrollment.course_id,
        status=enrollment.status.value,
        enrolled_at=enrollment.enrolled_at.isoformat(),
    )


@router.get("/student/courses", response_model=list[dict])
async def student_courses(
    current_user: dict = Depends(require_student),
    session: Session = Depends(get_session),
) -> list[dict]:
    """학생이 등록한 강의 목록 조회"""
    enrollments = session.exec(
        select(CourseEnrollment).where(
            CourseEnrollment.student_id == current_user["id"],
            CourseEnrollment.status == EnrollmentStatus.active,
        )
    ).all()
    
    courses = []
    for enrollment in enrollments:
        course = session.get(Course, enrollment.course_id)
        if course:
            courses.append({
                "id": course.id,
                "title": course.title,
                "status": course.status.value,
                "enrolled_at": enrollment.enrolled_at.isoformat(),
            })
    
    return courses


# ==================== 공통 엔드포인트 ====================

@router.get("/health")
def health_check() -> dict:
    return {"status": "ok", "service": "Yeop-Gang"}


@router.get("/status/{course_id}", response_model=DetailedStatusResponse)
async def get_status(
    course_id: str,
    current_user: dict = Depends(require_any_user),
    session: Session = Depends(get_session),
) -> DetailedStatusResponse:
    """처리 상태 조회 (권한 체크 포함)"""
    # 강의 접근 권한 확인
    await verify_course_access(course_id, current_user, session)
    
    course = session.get(Course, course_id)
    if not course:
        return DetailedStatusResponse(
            course_id=course_id,
            status="not_found",
            progress=0,
        )
    
    # 실제 진행도 필드 사용
    progress = getattr(course, 'progress', 0) if course.status == CourseStatus.processing else 100
    return DetailedStatusResponse(
        course_id=course_id,
        status=course.status.value,
        progress=progress,
    )


@router.get("/video/{course_id}")
async def get_video(
    course_id: str,
    current_user: dict = Depends(require_any_user),
    session: Session = Depends(get_session),
) -> FileResponse:
    """비디오/오디오 파일 조회 (권한 체크 포함) - mp4와 mp3 모두 지원"""
    # 강의 접근 권한 확인
    await verify_course_access(course_id, current_user, session)
    
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
    
    # Fallback
    ref_video = PROJECT_ROOT / "ref" / "video" / "testvedio_1.mp4"
    if ref_video.exists():
        return FileResponse(ref_video, media_type="video/mp4")
    
    raise HTTPException(status_code=404, detail="Video/Audio not found")


@router.post("/chat/ask", response_model=SafeChatResponse)
async def ask(
    payload: QueryRequest,
    current_user: dict = Depends(require_any_user),
    pipeline: RAGPipeline = Depends(get_pipeline),
    session: Session = Depends(get_session),
) -> SafeChatResponse:
    """챗봇 질의 (권한 체크 및 가드레일 적용)"""
    # 강의 접근 권한 확인
    await verify_course_access(payload.course_id, current_user, session)
    
    conversation_id = payload.conversation_id or f"{current_user['id']}:{payload.course_id}"
    
    # 간단한 대화 히스토리 (프로덕션에서는 DB 사용)
    if not hasattr(ask, '_conversation_history'):
        setattr(ask, '_conversation_history', {})
    history = getattr(ask, '_conversation_history', {}).get(conversation_id, [])
    
    # RAG 쿼리 실행
    result = pipeline.query(
        payload.question,
        course_id=payload.course_id,
        conversation_history=history
    )
    
    answer = result.get("answer", "")
    
    # 가드레일 적용
    filtered_answer, is_safe = apply_guardrails(answer)
    filtered = answer != filtered_answer
    
    # 대화 히스토리 업데이트
    history.append({"role": "user", "content": payload.question})
    history.append({"role": "assistant", "content": filtered_answer})
    if len(history) > 20:
        history = history[-20:]
    getattr(ask, '_conversation_history', {})[conversation_id] = history
    
    return SafeChatResponse(
        answer=filtered_answer,
        sources=[str(src) for src in result.get("documents", [])],
        conversation_id=conversation_id,
        course_id=payload.course_id,
        is_safe=is_safe,
        filtered=filtered,
    )

