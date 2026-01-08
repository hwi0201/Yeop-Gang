"""
개선된 비동기 Task 관리
- 백엔드 A의 processor.process_course_assets() 호출
- 진행률 추적
- 에러 핸들링
"""
import logging
from pathlib import Path
from typing import Optional, List
from datetime import datetime

from fastapi import BackgroundTasks
from sqlmodel import Session, select

from core.db import engine
from core.models import Course, CourseStatus, Video

logger = logging.getLogger(__name__)


def _split_text_into_chunks(text: str, model_name: str, max_tokens: int = 7000) -> List[str]:
    """
    텍스트를 토큰 길이 기준으로 청크로 분할합니다.
    embedding 모델의 최대 토큰 길이 제한을 고려하여 안전하게 분할합니다.
    
    Args:
        text: 분할할 텍스트
        model_name: 사용할 모델 이름 (tiktoken 인코딩용)
        max_tokens: 각 청크의 최대 토큰 수 (기본값: 7000, 안전 마진 포함)
    
    Returns:
        텍스트 청크 리스트
    """
    try:
        import tiktoken
    except ImportError:
        logger.warning("tiktoken not available, using character-based chunking")
        # tiktoken이 없으면 문자 수 기준으로 분할 (1 토큰 ≈ 4 문자 가정)
        chunk_size = max_tokens * 4
        chunks = []
        for i in range(0, len(text), chunk_size):
            chunks.append(text[i:i + chunk_size])
        return chunks
    
    try:
        # 모델에 맞는 인코더 가져오기
        encoding = tiktoken.encoding_for_model(model_name)
    except KeyError:
        # 모델을 찾을 수 없으면 cl100k_base (GPT-4/GPT-3.5용) 사용
        encoding = tiktoken.get_encoding("cl100k_base")
        logger.warning(f"Encoding for model {model_name} not found, using cl100k_base")
    
    # 텍스트를 토큰으로 인코딩
    tokens = encoding.encode(text)
    
    if len(tokens) <= max_tokens:
        # 토큰 수가 제한 이하이면 그대로 반환
        return [text]
    
    # 토큰을 청크로 분할
    chunks = []
    for i in range(0, len(tokens), max_tokens):
        chunk_tokens = tokens[i:i + max_tokens]
        chunk_text = encoding.decode(chunk_tokens)
        chunks.append(chunk_text)
    
    logger.info(f"Split text into {len(chunks)} chunks (total tokens: {len(tokens)}, max per chunk: {max_tokens})")
    return chunks


def enqueue_processing_task(
    tasks: BackgroundTasks,
    *,
    course_id: str,
    instructor_id: str,
    video_path: Optional[Path] = None,
    audio_path: Optional[Path] = None,
    pdf_path: Optional[Path] = None,
    smi_path: Optional[Path] = None,
) -> None:
    """
    백그라운드 처리 작업 등록
    백엔드 A의 processor.process_course_assets()를 호출합니다.
    """
    tasks.add_task(
        process_course_assets_wrapper,
        course_id=course_id,
        instructor_id=instructor_id,
        video_path=video_path,
        audio_path=audio_path,
        pdf_path=pdf_path,
        smi_path=smi_path,
    )


def process_course_assets_wrapper(
    *,
    course_id: str,
    instructor_id: str,
    video_path: Optional[Path] = None,
    audio_path: Optional[Path] = None,
    pdf_path: Optional[Path] = None,
    smi_path: Optional[Path] = None,
) -> None:
    """
    백엔드 A의 processor.process_course_assets()를 호출하는 래퍼 함수
    백엔드 B는 이 함수를 통해 백엔드 A의 처리 로직을 호출합니다.
    """
    try:
        # 경로를 절대 경로로 변환
        if video_path:
            video_path = Path(video_path).resolve()
            logger.info(f"📁 Video path resolved: {video_path} (exists: {video_path.exists()})")
        if audio_path:
            audio_path = Path(audio_path).resolve()
            logger.info(f"📁 Audio path resolved: {audio_path} (exists: {audio_path.exists()})")
        if pdf_path:
            pdf_path = Path(pdf_path).resolve()
            logger.info(f"📁 PDF path resolved: {pdf_path} (exists: {pdf_path.exists()})")
        if smi_path:
            smi_path = Path(smi_path).resolve()
            logger.info(f"📁 SMI path resolved: {smi_path} (exists: {smi_path.exists()})")
        
        # 진행도 초기화
        _update_progress(course_id, 0, "처리 시작")
        
        # 백엔드 A의 processor 모듈 import 시도
        try:
            from ai.pipelines.processor import process_course_assets
            # 백엔드 A의 함수가 있으면 호출
            _update_progress(course_id, 10, "파이프라인 시작")
            
            # 진행률 업데이트 콜백 함수 생성
            def update_progress_callback(progress: int, message: str) -> None:
                _update_progress(course_id, progress, message)
            
            result = process_course_assets(
                course_id=course_id,
                instructor_id=instructor_id,
                video_path=video_path,
                audio_path=audio_path,
                pdf_path=pdf_path,
                smi_path=smi_path,
                update_progress=update_progress_callback,
            )
            
            # 처리 결과 확인
            if result.get("status") == "completed":
                ingested_count = result.get("ingested_count", 0)
                transcript_path = result.get("transcript_path")  # STT 결과 파일 경로
                logger.info(f"Course {course_id} processed successfully via backend A processor (ingested: {ingested_count})")
                _update_progress(course_id, 100, f"처리 완료 (인제스트: {ingested_count}개)")
                
                # DB 상태를 completed로 업데이트 및 transcript_path 저장
                with Session(engine) as session:
                    course = session.get(Course, course_id)
                    if course:
                        course.status = CourseStatus.completed
                        course.progress = 100
                        session.commit()
                    
                    # Video/Audio 레코드에 transcript_path 저장
                    if transcript_path:
                        # video_path 또는 audio_path 중 처리된 것 찾기
                        target_path = video_path or audio_path
                        if target_path:
                            videos = session.exec(
                                select(Video).where(
                                    Video.course_id == course_id,
                                    Video.filename == target_path.name
                                )
                            ).all()
                            for vid in videos:
                                vid.transcript_path = transcript_path
                            session.commit()
                            logger.info(f"Transcript path saved to Video record: {transcript_path}")
            else:
                # 처리 실패
                error_msg = result.get("error", "알 수 없는 오류")
                logger.error(f"Course {course_id} processing failed: {error_msg}")
                _update_progress(course_id, 0, f"처리 실패: {error_msg}")
                
                # DB 상태를 failed로 업데이트
                with Session(engine) as session:
                    course = session.get(Course, course_id)
                    if course:
                        course.status = CourseStatus.failed
                        session.commit()
                        
        except ImportError:
            # 백엔드 A의 processor.py가 아직 없으면 기존 로직 사용 (임시)
            logger.warning(
                "Backend A processor.py not found. Using fallback processing. "
                "This should be replaced when processor.py is implemented."
            )
            _fallback_process_course_assets(
                course_id=course_id,
                instructor_id=instructor_id,
                video_path=video_path,
                audio_path=audio_path,
                pdf_path=pdf_path,
                smi_path=smi_path,
            )
    except Exception as e:
        logger.error(f"Error processing course {course_id}: {e}", exc_info=True)
        _update_progress(course_id, 0, f"오류 발생: {str(e)}")
        # DB에 실패 상태 저장
        
        with Session(engine) as session:
            course = session.get(Course, course_id)
            if course:
                course.status = CourseStatus.failed
                # 에러 메시지를 progress 필드나 다른 방법으로 저장할 수 있지만,
                # 일단 로그에 남기고 상태만 저장
                session.commit()
                logger.error(f"Course {course_id} marked as failed. Error: {error_msg}")


def _update_progress(course_id: str, progress: int, message: Optional[str] = None) -> None:
    """
    진행도를 업데이트하는 헬퍼 함수
    
    Args:
        course_id: 강의 ID
        progress: 진행도 (0-100)
        message: 진행 상황 메시지 (옵션)
    """
    from sqlmodel import Session
    from core.models import Course
    
    with Session(engine) as session:
        course = session.get(Course, course_id)
        if course:
            course.progress = max(0, min(100, progress))  # 0-100 범위로 제한
            session.commit()
            if message:
                logger.info(f"Progress updated for course {course_id}: {progress}% - {message}")
            else:
                logger.info(f"Progress updated for course {course_id}: {progress}%")


def _fallback_process_course_assets(
    *,
    course_id: str,
    instructor_id: str,
    video_path: Optional[Path] = None,
    audio_path: Optional[Path] = None,
    pdf_path: Optional[Path] = None,
    smi_path: Optional[Path] = None,
) -> None:
    """
    폴백 처리 함수 - 실제 STT, 임베딩, 페르소나 생성 수행
    백엔드 A의 processor.py가 없을 때 사용됩니다.
    프론트엔드에서 업로드하면 자동으로 이 함수가 실행되어 처리됩니다.
    """
    from sqlmodel import Session
    from core.models import Course, CourseStatus, Video
    from ai.config import AISettings
    from ai.pipelines.rag import RAGPipeline
    from ai.services.stt import transcribe_video
    
    settings = AISettings()
    pipeline = RAGPipeline(settings)
    
    with Session(engine) as session:
        course = session.get(Course, course_id)
        if not course:
            course = Course(id=course_id, instructor_id=instructor_id)
            session.add(course)
        course.status = CourseStatus.processing
        course.progress = 0
        session.commit()
        
        logger.info(f"Starting processing for course {course_id}")
        texts: list[str] = []
        
        # SMI 자막 파일이 있으면 STT 건너뛰고 SMI 파싱
        if smi_path:
            try:
                logger.info(f"📝 SMI subtitle file detected: {smi_path}")
                _update_progress(course_id, 10, "SMI 자막 파일 파싱 중...")
                
                from ai.services.smi_parser import parse_smi_file
                import json
                
                # SMI 파일 파싱
                transcript_result = parse_smi_file(smi_path)
                transcript_text = transcript_result.get("text", "")
                segments = transcript_result.get("segments", [])
                
                logger.info(f"✅ SMI parsed: {len(transcript_text)} chars, {len(segments)} segments")
                
                # Transcript JSON 저장
                from core.config import AppSettings
                app_settings = AppSettings()
                course_dir = app_settings.uploads_dir / instructor_id / course_id
                course_dir.mkdir(parents=True, exist_ok=True)
                
                transcript_filename = f"transcript_{smi_path.stem}.json"
                transcript_file_path = course_dir / transcript_filename
                
                transcript_data = {
                    "text": transcript_text,
                    "segments": segments,
                    "source_file": smi_path.name,
                    "course_id": course_id,
                    "instructor_id": instructor_id,
                }
                
                with transcript_file_path.open("w", encoding="utf-8") as f:
                    json.dump(transcript_data, f, ensure_ascii=False, indent=2)
                
                logger.info(f"✅ Transcript JSON saved: {transcript_file_path}")
                
                _update_progress(course_id, 40, "SMI 자막 파일 파싱 완료")
                
                # 임베딩 처리로 진행
                if transcript_text:
                    texts.append(transcript_text)
                    
                    # 세그먼트 임베딩
                    _update_progress(course_id, 50, "자막 세그먼트 임베딩 중...")
                    for i, seg in enumerate(segments):
                        seg_text = seg.get("text", "")
                        if seg_text:
                            pipeline.ingest_text(
                                seg_text,
                                course_id=course_id,
                                metadata={
                                    "type": "audio_segment",
                                    "start": seg.get("start", 0.0),
                                    "end": seg.get("end", 0.0),
                                    "start_formatted": seg.get("start_formatted", ""),
                                    "end_formatted": seg.get("end_formatted", ""),
                                }
                            )
                    _update_progress(course_id, 60, "자막 세그먼트 임베딩 완료")
                
            except Exception as e:
                logger.error(f"❌ SMI parsing failed: {e}")
                import traceback
                logger.error(traceback.format_exc())
                raise
        
        # 오디오 파일 우선 처리 (MP3 등), 없으면 비디오 처리
        elif audio_path:
            try:
                # 파일 경로 확인 및 정규화
                if not isinstance(audio_path, Path):
                    audio_path = Path(audio_path)
                
                # 절대 경로로 변환
                if not audio_path.is_absolute():
                    audio_path = audio_path.resolve()
                
                logger.info(f"📁 Audio file path: {audio_path}")
                logger.info(f"📁 Audio file exists: {audio_path.exists()}")
                
                if not audio_path.exists():
                    # 파일이 없으면 상대 경로로도 시도
                    from core.config import AppSettings
                    app_settings = AppSettings()
                    potential_path = app_settings.uploads_dir / instructor_id / course_id / audio_path.name
                    if potential_path.exists():
                        audio_path = potential_path.resolve()
                        logger.info(f"📁 Found audio file at alternative path: {audio_path}")
                    else:
                        error_msg = f"오디오 파일을 찾을 수 없습니다: {audio_path} (also tried: {potential_path})"
                        logger.error(f"❌ {error_msg}")
                        raise FileNotFoundError(error_msg)
                
                logger.info(f"🎤 Starting STT for audio: {audio_path}")
                _update_progress(course_id, 10, "오디오 음성 인식(STT) 시작 (무료 로컬 Whisper 사용)")
                
                # 로컬 Whisper 사용 (무료, API 키 불필요)
                logger.info(f"✅ Using local Whisper (FREE, no API key needed)")
                
                # 첫 업로드이므로 무조건 STT 실행
                logger.info(f"🔄 Running STT (force_retranscribe=True to ensure fresh transcription)...")
                transcript_result = transcribe_video(
                    str(audio_path), 
                    settings=settings,
                    transcript_path=None,  # 기존 파일 무시하고 새로 생성
                    force_retranscribe=True,  # 강제로 STT 실행
                    instructor_id=instructor_id,
                    course_id=course_id,
                )
                _update_progress(course_id, 40, "오디오 음성 인식(STT) 완료")
                transcript_text = transcript_result.get("text", "")
                segments = transcript_result.get("segments", [])
                
                logger.info(f"📝 STT result - text length: {len(transcript_text)}, segments: {len(segments)}")
                
                # STT 실패 체크 - placeholder나 에러 메시지면 저장하지 않음
                transcript_lower = transcript_text.lower()
                if ("placeholder" in transcript_lower or 
                    "transcription failed" in transcript_lower or
                    "error" in transcript_lower and "failed" in transcript_lower):
                    error_msg = f"오디오 STT가 실패했습니다: {transcript_text[:100]}"
                    logger.error(f"❌ {error_msg}")
                    raise ValueError(error_msg)
                
                if not transcript_text or not transcript_text.strip():
                    error_msg = f"오디오 STT 결과가 비어있습니다."
                    logger.error(f"❌ {error_msg}")
                    raise ValueError(error_msg)
                
                # STT 결과를 파일로 저장
                transcript_path = None
                if transcript_text:
                    try:
                        from core.config import AppSettings
                        import json
                        
                        app_settings = AppSettings()
                        course_dir = app_settings.uploads_dir / instructor_id / course_id
                        course_dir.mkdir(parents=True, exist_ok=True)
                        
                        # transcript 파일명: transcript_{원본파일명}.json
                        transcript_filename = f"transcript_{audio_path.stem}.json"
                        transcript_file_path = course_dir / transcript_filename
                        
                        # JSON 형식으로 저장 (전체 텍스트 + 세그먼트 정보)
                        transcript_data = {
                            "text": transcript_text,
                            "segments": segments,
                            "source_file": audio_path.name,
                            "course_id": course_id,
                            "instructor_id": instructor_id,
                        }
                        
                        logger.info(f"Attempting to save transcript to: {transcript_file_path}")
                        logger.info(f"Transcript text length: {len(transcript_text)}")
                        
                        with transcript_file_path.open("w", encoding="utf-8") as f:
                            json.dump(transcript_data, f, ensure_ascii=False, indent=2)
                        
                        # 파일이 실제로 저장되었는지 확인
                        if transcript_file_path.exists():
                            file_size = transcript_file_path.stat().st_size
                            transcript_path = str(transcript_file_path)
                            logger.info(f"✅ STT transcript JSON saved successfully: {transcript_path} (size: {file_size} bytes)")
                        else:
                            logger.error(f"❌ Transcript file was not created: {transcript_file_path}")
                    except Exception as e:
                        import traceback
                        logger.error(f"❌ Failed to save transcript file: {e}")
                        logger.error(f"Error details: {traceback.format_exc()}")
                        # 파일 저장 실패해도 계속 진행
                
                if transcript_text:
                    # 전체 텍스트 저장
                    texts.append(transcript_text)
                    
                    # 세그먼트별로 임베딩 및 벡터 DB 저장 (타임스탬프 포함)
                    logger.info(f"Processing {len(segments)} audio segments for embedding")
                    segment_texts = []
                    for seg in segments:
                        seg_text = seg.get("text", "").strip()
                        if seg_text:
                            start_time = seg.get("start", 0.0)
                            segment_texts.append(seg_text)
                    
                    if segment_texts:
                        _update_progress(course_id, 50, "오디오 세그먼트 임베딩 생성 중")
                        ingested = pipeline.ingest_texts(
                            segment_texts,
                            course_id=course_id,
                            metadata={"source": "audio", "filename": audio_path.name}
                        )
                        ingested_count = ingested.get("ingested_count", 0)
                        _update_progress(course_id, 60, "오디오 세그먼트 임베딩 완료")
                        logger.info(f"✅ Ingested {ingested_count} audio segments into vector DB")
                
                # Audio 레코드 생성
                absolute_path = audio_path.resolve()
                vid = Video(
                    course_id=course_id,
                    filename=audio_path.name,
                    storage_path=str(absolute_path),
                    filetype="audio",
                    transcript_path=transcript_path,
                )
                session.add(vid)
                session.commit()
                logger.info(f"Audio record created: {audio_path.name}, transcript_path: {transcript_path}")
                
            except (FileNotFoundError, ValueError) as e:
                error_msg = f"오디오 STT 처리 오류 ({audio_path.name if audio_path else 'unknown'}): {str(e)}"
                logger.error(f"❌ {error_msg}")
                course.status = CourseStatus.failed
                course.progress = 0
                session.commit()
                raise Exception(error_msg)
            except Exception as e:
                error_msg = f"오디오 처리 중 예상치 못한 오류: {str(e)}"
                logger.error(f"❌ {error_msg}")
                import traceback
                logger.error(traceback.format_exc())
                course.status = CourseStatus.failed
                course.progress = 0
                session.commit()
                raise Exception(error_msg)
        
        # 비디오 처리 (STT) - 오디오 파일이 없을 때만
        elif video_path:
            try:
                # 파일 경로 확인 및 정규화
                video_path = Path(video_path).resolve()
                logger.info(f"📁 Video file path: {video_path}")
                logger.info(f"📁 Video file exists: {video_path.exists()}")
                logger.info(f"📁 Video file absolute path: {video_path.absolute()}")
                
                if not video_path.exists():
                    error_msg = f"비디오 파일을 찾을 수 없습니다: {video_path}"
                    logger.error(f"❌ {error_msg}")
                    raise FileNotFoundError(error_msg)
                
                logger.info(f"🎤 Starting STT for video: {video_path}")
                _update_progress(course_id, 10, "음성 인식(STT) 시작 (무료 로컬 Whisper 사용)")
                
                # 로컬 Whisper 사용 (무료, API 키 불필요)
                logger.info(f"✅ Using local Whisper (FREE, no API key needed)")
                
                # 첫 업로드이므로 무조건 STT 실행 (force_retranscribe=True)
                # 기존 transcript 파일이 있어도 재생성 (한 번만 실행되도록 보장)
                logger.info(f"🔄 Running STT (force_retranscribe=True to ensure fresh transcription)...")
                transcript_result = transcribe_video(
                    str(video_path), 
                    settings=settings,
                    transcript_path=None,  # 기존 파일 무시하고 새로 생성
                    force_retranscribe=True,  # 강제로 STT 실행
                    instructor_id=instructor_id,
                    course_id=course_id,
                )
                _update_progress(course_id, 40, "음성 인식(STT) 완료")
                transcript_text = transcript_result.get("text", "")
                segments = transcript_result.get("segments", [])
                
                logger.info(f"📝 STT result - text length: {len(transcript_text)}, segments: {len(segments)}")
                
                # STT 실패 체크 - placeholder나 에러 메시지면 저장하지 않음
                transcript_lower = transcript_text.lower()
                if ("placeholder" in transcript_lower or 
                    "transcription failed" in transcript_lower or
                    "failed:" in transcript_lower or
                    "error" in transcript_lower):
                    error_msg = (
                        f"❌ STT가 실패했습니다. "
                        f"반환된 메시지: {transcript_text[:200]}... "
                        f"서버 로그를 확인하세요."
                    )
                    logger.error(error_msg)
                    raise ValueError(error_msg)
                
                if not transcript_text or not transcript_text.strip():
                    error_msg = "STT 결과가 비어있습니다. 서버 로그를 확인하세요."
                    logger.error(f"❌ {error_msg}")
                    raise ValueError(error_msg)
                
                logger.info(f"✅ STT 성공! 전사된 텍스트 길이: {len(transcript_text)} 문자")
                
                # STT 결과를 파일로 저장
                transcript_path = None
                if transcript_text:
                    try:
                        from core.config import AppSettings
                        import json
                        
                        app_settings = AppSettings()
                        course_dir = app_settings.uploads_dir / instructor_id / course_id
                        course_dir.mkdir(parents=True, exist_ok=True)
                        
                        # transcript 파일명: transcript_{원본파일명}.json
                        transcript_filename = f"transcript_{video_path.stem}.json"
                        transcript_file_path = course_dir / transcript_filename
                        
                        # JSON 형식으로 저장 (전체 텍스트 + 세그먼트 정보)
                        transcript_data = {
                            "text": transcript_text,
                            "segments": segments,
                            "source_file": video_path.name,
                            "course_id": course_id,
                            "instructor_id": instructor_id,
                        }
                        
                        logger.info(f"Attempting to save transcript to: {transcript_file_path}")
                        logger.info(f"Transcript text length: {len(transcript_text)}")
                        
                        with transcript_file_path.open("w", encoding="utf-8") as f:
                            json.dump(transcript_data, f, ensure_ascii=False, indent=2)
                        
                        # 파일이 실제로 저장되었는지 확인
                        if transcript_file_path.exists():
                            file_size = transcript_file_path.stat().st_size
                            transcript_path = str(transcript_file_path)
                            logger.info(f"✅ STT transcript JSON saved successfully: {transcript_path} (size: {file_size} bytes)")
                        else:
                            logger.error(f"❌ Transcript file was not created: {transcript_file_path}")
                    except Exception as e:
                        import traceback
                        logger.error(f"❌ Failed to save transcript file: {e}")
                        logger.error(f"Error details: {traceback.format_exc()}")
                        # 파일 저장 실패해도 계속 진행
                
                if transcript_text:
                    # 전체 텍스트 저장
                    texts.append(transcript_text)
                    
                    # 세그먼트별로 임베딩 및 벡터 DB 저장 (타임스탬프 포함)
                    logger.info(f"Processing {len(segments)} segments for embedding")
                    segment_texts = []
                    segment_metas = []
                    for idx, seg in enumerate(segments):
                        seg_text = seg.get("text", "")
                        if not seg_text:
                            continue
                        seg_meta = {
                            "course_id": course_id,
                            "instructor_id": instructor_id,
                            "source": video_path.name,
                            "start_time": seg.get("start"),
                            "end_time": seg.get("end"),
                            "segment_index": idx,
                            "type": "segment",
                        }
                        segment_texts.append(seg_text)
                        segment_metas.append(seg_meta)
                    
                    # 세그먼트들을 한 번에 저장 (고유 ID 보장)
                    if segment_texts:
                        from ai.services.embeddings import embed_texts
                        from ai.services.vectorstore import get_chroma_client, get_collection
                        
                        _update_progress(course_id, 50, "세그먼트 임베딩 생성 중")
                        embeddings = embed_texts(segment_texts, settings)
                        client = get_chroma_client(settings)
                        collection = get_collection(client, settings)
                        
                        # 고유 ID 생성: course_id-segment-{index}
                        segment_ids = [f"{course_id}-segment-{i}" for i in range(len(segment_texts))]
                        
                        collection.upsert(
                            ids=segment_ids,
                            documents=segment_texts,
                            metadatas=segment_metas,
                            embeddings=embeddings,
                        )
                        _update_progress(course_id, 60, "세그먼트 임베딩 완료")
                        logger.info(f"Stored {len(segment_texts)} segments to vector DB")
                
                # Video/Audio 레코드 생성 (파일 확장자로 타입 판단)
                file_ext = video_path.suffix.lower()
                if file_ext in [".mp3", ".wav", ".m4a", ".aac", ".ogg", ".flac"]:
                    file_type = "audio"
                elif file_ext in [".mp4", ".avi", ".mov", ".mkv", ".webm"]:
                    file_type = "video"
                else:
                    file_type = "video"  # 기본값
                
                # 절대 경로로 변환하여 저장
                absolute_path = video_path.resolve()
                vid = Video(
                    course_id=course_id,
                    filename=video_path.name,
                    storage_path=str(absolute_path),
                    filetype=file_type,
                    transcript_path=transcript_path,  # STT 결과 파일 경로 저장
                )
                session.add(vid)
                session.commit()
                logger.info(f"Video record created: {video_path.name}, transcript_path: {transcript_path}")
                
            except FileNotFoundError as e:
                error_msg = f"파일을 찾을 수 없습니다: {e}"
                logger.error(f"Video processing error: {error_msg}", exc_info=True)
                course.status = CourseStatus.failed
                session.commit()
                raise Exception(error_msg)
            except ValueError as e:
                error_msg = str(e)
                logger.error(f"Video processing error: {error_msg}", exc_info=True)
                course.status = CourseStatus.failed
                session.commit()
                raise Exception(error_msg)
            except Exception as e:
                error_msg = f"비디오 처리 중 오류 발생: {str(e)}"
                logger.error(f"Video processing error: {error_msg}", exc_info=True)
                course.status = CourseStatus.failed
                session.commit()
                raise Exception(error_msg)
        
        # 오디오 처리 (STT)
        if audio_path:
            try:
                # 파일 경로 확인 및 정규화
                if not isinstance(audio_path, Path):
                    audio_path = Path(audio_path)
                
                # 절대 경로로 변환
                if not audio_path.is_absolute():
                    audio_path = audio_path.resolve()
                
                logger.info(f"📁 Audio file path: {audio_path}")
                logger.info(f"📁 Audio file exists: {audio_path.exists()}")
                
                if not audio_path.exists():
                    # 파일이 없으면 상대 경로로도 시도
                    from core.config import AppSettings
                    app_settings = AppSettings()
                    potential_path = app_settings.uploads_dir / instructor_id / course_id / audio_path.name
                    if potential_path.exists():
                        audio_path = potential_path.resolve()
                        logger.info(f"📁 Found audio file at alternative path: {audio_path}")
                    else:
                        error_msg = f"오디오 파일을 찾을 수 없습니다: {audio_path} (also tried: {potential_path})"
                        logger.error(f"❌ {error_msg}")
                        raise FileNotFoundError(error_msg)
                
                logger.info(f"🎤 Starting STT for audio: {audio_path}")
                _update_progress(course_id, 10, "오디오 음성 인식(STT) 시작 (무료 로컬 Whisper 사용)")
                
                # 로컬 Whisper 사용 (무료, API 키 불필요)
                logger.info(f"✅ Using local Whisper (FREE, no API key needed)")
                
                # 첫 업로드이므로 무조건 STT 실행
                logger.info(f"🔄 Running STT (force_retranscribe=True to ensure fresh transcription)...")
                transcript_result = transcribe_video(
                    str(audio_path), 
                    settings=settings,
                    transcript_path=None,  # 기존 파일 무시하고 새로 생성
                    force_retranscribe=True,  # 강제로 STT 실행
                    instructor_id=instructor_id,
                    course_id=course_id,
                )
                _update_progress(course_id, 40, "오디오 음성 인식(STT) 완료")
                transcript_text = transcript_result.get("text", "")
                segments = transcript_result.get("segments", [])
                
                logger.info(f"📝 STT result - text length: {len(transcript_text)}, segments: {len(segments)}")
                
                # STT 실패 체크 - placeholder나 에러 메시지면 저장하지 않음
                transcript_lower = transcript_text.lower()
                if ("placeholder" in transcript_lower or 
                    "transcription failed" in transcript_lower or
                    "failed:" in transcript_lower or
                    "error" in transcript_lower):
                    error_msg = (
                        f"❌ STT가 실패했습니다. "
                        f"반환된 메시지: {transcript_text[:200]}... "
                        f"서버 로그를 확인하세요."
                    )
                    logger.error(error_msg)
                    raise ValueError(error_msg)
                
                if not transcript_text or not transcript_text.strip():
                    error_msg = "STT 결과가 비어있습니다. 서버 로그를 확인하세요."
                    logger.error(f"❌ {error_msg}")
                    raise ValueError(error_msg)
                
                logger.info(f"✅ STT 성공! 전사된 텍스트 길이: {len(transcript_text)} 문자")
                
                # STT 결과를 파일로 저장
                transcript_path = None
                if transcript_text:
                    try:
                        from core.config import AppSettings
                        import json
                        
                        app_settings = AppSettings()
                        course_dir = app_settings.uploads_dir / instructor_id / course_id
                        course_dir.mkdir(parents=True, exist_ok=True)
                        
                        # transcript 파일명: transcript_{원본파일명}.json
                        transcript_filename = f"transcript_{audio_path.stem}.json"
                        transcript_file_path = course_dir / transcript_filename
                        
                        # JSON 형식으로 저장 (전체 텍스트 + 세그먼트 정보)
                        transcript_data = {
                            "text": transcript_text,
                            "segments": segments,
                            "source_file": audio_path.name,
                            "course_id": course_id,
                            "instructor_id": instructor_id,
                        }
                        
                        logger.info(f"Attempting to save transcript to: {transcript_file_path}")
                        logger.info(f"Transcript text length: {len(transcript_text)}")
                        
                        with transcript_file_path.open("w", encoding="utf-8") as f:
                            json.dump(transcript_data, f, ensure_ascii=False, indent=2)
                        
                        # 파일이 실제로 저장되었는지 확인
                        if transcript_file_path.exists():
                            file_size = transcript_file_path.stat().st_size
                            transcript_path = str(transcript_file_path)
                            logger.info(f"✅ STT transcript JSON saved successfully: {transcript_path} (size: {file_size} bytes)")
                        else:
                            logger.error(f"❌ Transcript file was not created: {transcript_file_path}")
                    except Exception as e:
                        import traceback
                        logger.error(f"❌ Failed to save transcript file: {e}")
                        logger.error(f"Error details: {traceback.format_exc()}")
                        # 파일 저장 실패해도 계속 진행
                
                if transcript_text:
                    # 전체 텍스트 저장
                    texts.append(transcript_text)
                    
                    # 세그먼트별로 임베딩 및 벡터 DB 저장 (타임스탬프 포함)
                    logger.info(f"Processing {len(segments)} audio segments for embedding")
                    segment_texts = []
                    segment_metas = []
                    for idx, seg in enumerate(segments):
                        seg_text = seg.get("text", "")
                        if not seg_text:
                            continue
                        seg_meta = {
                            "course_id": course_id,
                            "instructor_id": instructor_id,
                            "source": audio_path.name,
                            "start_time": seg.get("start"),
                            "end_time": seg.get("end"),
                            "segment_index": idx,
                            "type": "segment",
                        }
                        segment_texts.append(seg_text)
                        segment_metas.append(seg_meta)
                    
                    # 세그먼트들을 한 번에 저장 (고유 ID 보장)
                    if segment_texts:
                        from ai.services.embeddings import embed_texts
                        from ai.services.vectorstore import get_chroma_client, get_collection
                        
                        _update_progress(course_id, 50, "오디오 세그먼트 임베딩 생성 중")
                        embeddings = embed_texts(segment_texts, settings)
                        client = get_chroma_client(settings)
                        collection = get_collection(client, settings)
                        
                        # 고유 ID 생성: course_id-audio-segment-{index}
                        segment_ids = [f"{course_id}-audio-segment-{i}" for i in range(len(segment_texts))]
                        
                        collection.upsert(
                            ids=segment_ids,
                            documents=segment_texts,
                            metadatas=segment_metas,
                            embeddings=embeddings,
                        )
                        _update_progress(course_id, 60, "오디오 세그먼트 임베딩 완료")
                        logger.info(f"Stored {len(segment_texts)} audio segments to vector DB")
                
                # Audio 레코드 생성 (절대 경로로 변환)
                absolute_audio_path = audio_path.resolve()
                audio_file = Video(
                    course_id=course_id,
                    filename=audio_path.name,
                    storage_path=str(absolute_audio_path),
                    filetype="audio",
                    transcript_path=transcript_path,  # STT 결과 파일 경로 저장
                )
                session.add(audio_file)
                session.commit()
                logger.info(f"Audio record created: {audio_path.name}, transcript_path: {transcript_path}")
                
            except Exception as e:
                logger.error(f"Audio processing error: {e}", exc_info=True)
                course.status = CourseStatus.failed
                session.commit()
                return
        
        # PDF 처리 (현재는 플레이스홀더)
        if pdf_path:
            try:
                logger.info(f"Processing PDF: {pdf_path}")
                # TODO: PDF 처리 로직 추가 (백엔드 A에서 구현 예정)
                pdf_text = f"PDF placeholder for {pdf_path.name}"
                texts.append(pdf_text)
                
                # PDF 레코드 생성 (절대 경로로 변환)
                absolute_pdf_path = pdf_path.resolve()
                doc = Video(
                    course_id=course_id,
                    filename=pdf_path.name,
                    storage_path=str(absolute_pdf_path),
                    filetype="pdf",
                )
                session.add(doc)
                session.commit()
                logger.info(f"PDF record created: {pdf_path.name}")
            except Exception as e:
                logger.error(f"PDF processing error: {e}", exc_info=True)
        
        # 전체 텍스트 임베딩 및 벡터 DB 저장 (세그먼트는 이미 저장됨)
        logger.info(f"📊 Total texts collected: {len(texts)}")
        if texts:
            try:
                from ai.services.embeddings import embed_texts
                from ai.services.vectorstore import get_chroma_client, get_collection
                
                # 전체 텍스트도 저장 (검색 성능 향상)
                logger.info("Ingesting full texts to vector DB")
                full_text = "\n\n".join(texts)
                
                if not full_text or len(full_text.strip()) == 0:
                    raise ValueError("전사된 텍스트가 없습니다. STT 처리가 실패했을 수 있습니다.")
                
                # 텍스트를 토큰 길이 기준으로 청크로 분할
                _update_progress(course_id, 70, "전체 텍스트 임베딩 준비 중")
                text_chunks = _split_text_into_chunks(full_text, settings.embedding_model, max_tokens=7000)
                
                client = get_chroma_client(settings)
                collection = get_collection(client, settings)
                
                # 각 청크에 대해 임베딩 생성 및 저장
                if len(text_chunks) == 1:
                    # 청크가 하나면 기존 방식과 동일하게 처리
                    embeddings = embed_texts([full_text], settings)
                    collection.upsert(
                        ids=[f"{course_id}-full"],
                        documents=[full_text],
                        metadatas=[{
                            "course_id": course_id,
                            "instructor_id": instructor_id,
                            "type": "full_text",
                        }],
                        embeddings=embeddings,
                    )
                else:
                    # 여러 청크인 경우 각각 임베딩 생성
                    embeddings = embed_texts(text_chunks, settings)
                    chunk_ids = [f"{course_id}-full-{i}" for i in range(len(text_chunks))]
                    chunk_metadatas = [{
                        "course_id": course_id,
                        "instructor_id": instructor_id,
                        "type": "full_text",
                        "chunk_index": i,
                        "total_chunks": len(text_chunks),
                    } for i in range(len(text_chunks))]
                    
                    collection.upsert(
                        ids=chunk_ids,
                        documents=text_chunks,
                        metadatas=chunk_metadatas,
                        embeddings=embeddings,
                    )
                
                _update_progress(course_id, 80, "전체 텍스트 임베딩 완료")
                logger.info(f"Full text stored to vector DB ({len(text_chunks)} chunk(s))")
                
                # 페르소나 프롬프트 생성 및 저장
                logger.info("Generating persona prompt")
                _update_progress(course_id, 85, "페르소나 프롬프트 생성 중")
                persona_prompt = pipeline.generate_persona_prompt(
                    course_id=course_id, sample_texts=texts
                )
                
                persona_embeddings = embed_texts([persona_prompt], settings)
                collection.upsert(
                    ids=[f"{course_id}-persona"],
                    documents=[persona_prompt],
                    metadatas=[{
                        "course_id": course_id,
                        "instructor_id": instructor_id,
                        "type": "persona",
                    }],
                    embeddings=persona_embeddings,
                )
                _update_progress(course_id, 95, "페르소나 프롬프트 생성 완료")
                logger.info("Persona prompt generated and stored")
            except ValueError as e:
                error_msg = str(e)
                logger.error(f"Vector DB ingestion error: {error_msg}", exc_info=True)
                course.status = CourseStatus.failed
                session.commit()
                raise Exception(error_msg)
            except Exception as e:
                error_msg = f"벡터 DB 저장 중 오류 발생: {str(e)}"
                logger.error(f"Vector DB ingestion error: {error_msg}", exc_info=True)
                course.status = CourseStatus.failed
                course.progress = 0
                session.commit()
                raise Exception(error_msg)
        else:
            logger.warning(f"⚠️ No texts to embed. STT may have failed or returned empty text.")
        
        # 처리 완료 (texts가 없어도 STT가 완료되었으면 완료로 표시)
        course = session.get(Course, course_id)
        if course:
            course.status = CourseStatus.completed
            course.progress = 100
            course.updated_at = datetime.utcnow()
            session.commit()
            logger.info(f"✅ Course {course_id} processing completed successfully (progress: 100%)")

