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
    SummaryRequest,
    SummaryResponse,
    QuizRequest,
    QuizResponse,
    QuizSubmitRequest,
    QuizResult,
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


@router.get("/courses")
def list_courses(session: Session = Depends(get_session)) -> list[dict]:
    """
    모든 강의 목록 조회 (학생용)
    """
    courses = session.exec(select(Course)).all()
    
    return [
        {
            "id": course.id,
            "title": course.title or course.id,
            "status": course.status.value,
            "instructor_id": course.instructor_id,
            "created_at": course.created_at.isoformat() if course.created_at else None,
            "progress": getattr(course, "progress", 0),
        }
        for course in courses
    ]


@router.delete("/courses/{course_id}")
def delete_course(course_id: str, session: Session = Depends(get_session)) -> dict:
    """
    강의 삭제 (DB, 벡터 DB, 업로드 파일 모두 삭제)
    """
    from pathlib import Path
    import shutil
    from core.config import AppSettings
    from ai.config import AISettings
    from ai.services.vectorstore import get_chroma_client, get_collection
    
    # 1. DB에서 강의 확인
    course = session.get(Course, course_id)
    if not course:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"강의를 찾을 수 없습니다: {course_id}")
    
    instructor_id = course.instructor_id
    
    # 2. 관련 데이터 삭제 (Video, ChatSession)
    videos = session.exec(select(Video).where(Video.course_id == course_id)).all()
    for video in videos:
        session.delete(video)
    
    from core.models import ChatSession
    sessions = session.exec(select(ChatSession).where(ChatSession.course_id == course_id)).all()
    for sess in sessions:
        session.delete(sess)
    
    # 3. 강의 삭제
    session.delete(course)
    session.commit()
    
    # 4. 벡터 DB에서 강의 데이터 삭제
    try:
        ai_settings = AISettings()
        client = get_chroma_client(ai_settings)
        collection = get_collection(client, ai_settings)
        
        # course_id로 필터링하여 삭제
        results = collection.get(where={"course_id": course_id})
        if results and results.get("ids"):
            collection.delete(ids=results["ids"])
    except Exception as e:
        print(f"벡터 DB 삭제 중 오류 (무시): {e}")
    
    # 5. 업로드 파일 삭제
    try:
        settings = AppSettings()
        uploads_dir = settings.uploads_dir
        if not uploads_dir.is_absolute():
            uploads_dir = Path(__file__).resolve().parents[2] / uploads_dir
        
        course_dir = uploads_dir / instructor_id / course_id
        if course_dir.exists():
            shutil.rmtree(course_dir)
    except Exception as e:
        print(f"파일 삭제 중 오류 (무시): {e}")
    
    return {
        "message": f"강의 '{course_id}'가 삭제되었습니다.",
        "course_id": course_id,
    }


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
        return StatusResponse(course_id=course_id, status="not_found", progress=0, message="강의를 찾을 수 없습니다.")

    # 실제 진행도 필드 사용
    progress = getattr(course, 'progress', 0) if course.status == CourseStatus.processing else 100
    
    # 실패 상태일 때 도움말 메시지 추가
    message = None
    if course.status == CourseStatus.failed:
        message = "서버 로그를 확인하세요. 일반적인 원인: OPENAI_API_KEY 미설정, 파일 형식 오류, 네트워크 문제"
    
    return StatusResponse(
        course_id=course_id,
        status=course.status.value,
        progress=progress,
        message=message,
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
    
    try:
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
    except Exception as e:
        error_msg = str(e)
        # OpenAI 할당량 에러 처리
        if "할당량" in error_msg or "quota" in error_msg.lower() or "insufficient_quota" in error_msg:
            answer = "⚠️ OpenAI API 할당량이 초과되었습니다. OpenAI 계정의 크레딧을 확인하거나 결제 정보를 업데이트하세요. https://platform.openai.com/account/billing"
        else:
            answer = f"⚠️ 오류 발생: {error_msg}"
        
        return ChatResponse(
            answer=answer,
            sources=[],
            conversation_id=conversation_id,
            course_id=payload.course_id,
        )


@router.post("/summary", response_model=SummaryResponse)
def generate_summary(
    payload: SummaryRequest,
    pipeline: RAGPipeline = Depends(get_pipeline),
) -> SummaryResponse:
    """
    강의 요약노트 생성
    """
    summary_prompt = (
        "이 강의의 핵심 내용을 요약해주세요. "
        "다음 형식으로 작성해주세요:\n\n"
        "1. 전체 요약 (2-3문단)\n"
        "2. 주요 포인트를 불릿 포인트로 나열 (최대 10개)\n"
        "각 포인트는 한 문장으로 간결하게 작성해주세요."
    )
    
    result = pipeline.query(
        summary_prompt,
        course_id=payload.course_id,
        k=8,  # 더 많은 컨텍스트 가져오기
    )
    
    answer = result.get("answer", "")
    
    # 주요 포인트 추출 (불릿 포인트나 번호 목록 찾기)
    key_points = []
    lines = answer.split("\n")
    for line in lines:
        line = line.strip()
        # 불릿 포인트 또는 번호 목록 패턴
        if line.startswith(("•", "-", "·", "*")) or line.match(r"^\d+[\.\)]\s+"):
            point = line.lstrip("•-·*").strip()
            point = point.lstrip("0123456789.) ").strip()
            if point and len(point) > 10:  # 너무 짧은 것은 제외
                key_points.append(point)
        elif line.startswith("- ") or line.startswith("• "):
            point = line[2:].strip()
            if point and len(point) > 10:
                key_points.append(point)
    
    # 주요 포인트가 없으면 전체 요약에서 추출 시도
    if not key_points:
        # 문장 단위로 나누고 중요한 문장 추출
        sentences = answer.replace(". ", ".\n").split("\n")
        key_points = [s.strip() for s in sentences if len(s.strip()) > 20][:10]
    
    return SummaryResponse(
        course_id=payload.course_id,
        summary=answer,
        key_points=key_points[:10],  # 최대 10개
    )


@router.post("/quiz/generate", response_model=QuizResponse)
def generate_quiz(
    payload: QuizRequest,
    pipeline: RAGPipeline = Depends(get_pipeline),
) -> QuizResponse:
    """
    강의 기반 퀴즈 생성
    """
    num_questions = min(max(payload.num_questions, 1), 10)  # 1-10개 제한
    
    quiz_prompt = (
        f"이 강의 내용을 바탕으로 객관식 퀴즈 {num_questions}문제를 만들어주세요.\n\n"
        "각 문제마다 다음 형식으로 작성해주세요:\n"
        "문제1: [문제 내용]\n"
        "A. [선택지1]\n"
        "B. [선택지2]\n"
        "C. [선택지3]\n"
        "D. [선택지4]\n"
        "정답: A (또는 B, C, D)\n\n"
        "이런 형식으로 {num_questions}문제 만들어주세요."
    )
    
    result = pipeline.query(
        quiz_prompt,
        course_id=payload.course_id,
        k=8,  # 더 많은 컨텐스트 가져오기
    )
    
    answer = result.get("answer", "")
    
    # 퀴즈 파싱
    questions = _parse_quiz_from_text(answer, num_questions)
    
    return QuizResponse(
        course_id=payload.course_id,
        questions=questions,
        quiz_id=f"quiz-{payload.course_id}-{int(__import__('time').time())}",
    )


def _parse_quiz_from_text(text: str, num_questions: int) -> list:
    """
    LLM 응답 텍스트에서 퀴즈 문제 파싱
    """
    from api.schemas import QuizQuestion
    import re
    
    questions = []
    lines = text.split("\n")
    
    current_question = None
    question_id = 1
    
    for line in lines:
        line = line.strip()
        
        # 문제 시작 패턴
        if re.match(r"^문제\s*\d+[:：]?", line, re.IGNORECASE) or re.match(r"^\d+[\.\)]\s*", line):
            if current_question and current_question.get("options"):
                # 이전 문제 저장
                questions.append(QuizQuestion(**current_question))
            
            # 새 문제 시작
            question_text = re.sub(r"^문제\s*\d+[:：]?\s*", "", line, flags=re.IGNORECASE)
            question_text = re.sub(r"^\d+[\.\)]\s*", "", question_text)
            
            current_question = {
                "id": question_id,
                "question": question_text,
                "options": [],
                "correct_answer": 0,
            }
            question_id += 1
        
        # 선택지 패턴 (A. B. C. D. 또는 A) B) C) D))
        elif re.match(r"^[A-D][\.\)]\s+", line, re.IGNORECASE):
            if current_question:
                option_text = re.sub(r"^[A-D][\.\)]\s+", "", line, flags=re.IGNORECASE)
                current_question["options"].append(option_text)
        
        # 정답 패턴
        elif re.search(r"정답[:：]?\s*([A-D])", line, re.IGNORECASE):
            if current_question:
                match = re.search(r"정답[:：]?\s*([A-D])", line, re.IGNORECASE)
                if match:
                    answer_letter = match.group(1).upper()
                    current_question["correct_answer"] = ord(answer_letter) - ord("A")
        
        # 문제 내용에 추가 (선택지가 없을 때)
        elif line and current_question and len(current_question["options"]) == 0:
            if current_question["question"]:
                current_question["question"] += " " + line
            else:
                current_question["question"] = line
    
    # 마지막 문제 저장
    if current_question and current_question.get("options") and len(current_question["options"]) >= 2:
        # 선택지가 4개가 아니면 채우기
        while len(current_question["options"]) < 4:
            current_question["options"].append(f"선택지 {len(current_question['options']) + 1}")
        questions.append(QuizQuestion(**current_question))
    
    # 최대 개수 제한
    return questions[:num_questions]


@router.post("/quiz/submit", response_model=QuizResult)
def submit_quiz(
    payload: QuizSubmitRequest,
    pipeline: RAGPipeline = Depends(get_pipeline),
) -> QuizResult:
    """
    퀴즈 답변 제출 및 채점
    """
    # 퀴즈 재생성하여 정답 확인 (실제로는 DB에 저장된 퀴즈를 조회해야 함)
    # 여기서는 간단하게 재생성
    quiz_request = QuizRequest(course_id=payload.course_id, num_questions=5)
    quiz_response = generate_quiz(quiz_request, pipeline)
    
    correct_answers = []
    wrong_answers = []
    
    for question in quiz_response.questions:
        user_answer = payload.answers.get(question.id)
        if user_answer is not None:
            if user_answer == question.correct_answer:
                correct_answers.append(question.id)
            else:
                wrong_answers.append(question.id)
    
    total = len(quiz_response.questions)
    score = len(correct_answers)
    percentage = round((score / total * 100) if total > 0 else 0, 1)
    
    return QuizResult(
        course_id=payload.course_id,
        score=score,
        total=total,
        percentage=percentage,
        correct_answers=correct_answers,
        wrong_answers=wrong_answers,
    )

