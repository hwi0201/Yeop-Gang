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
from sqlmodel import Session

from core.db import engine
from core.models import Course, CourseStatus

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
    )


def process_course_assets_wrapper(
    *,
    course_id: str,
    instructor_id: str,
    video_path: Optional[Path] = None,
    audio_path: Optional[Path] = None,
    pdf_path: Optional[Path] = None,
) -> None:
    """
    백엔드 A의 processor.process_course_assets()를 호출하는 래퍼 함수
    백엔드 B는 이 함수를 통해 백엔드 A의 처리 로직을 호출합니다.
    """
    try:
        # 백엔드 A의 processor 모듈 import 시도
        try:
            from ai.pipelines.processor import process_course_assets
            # 백엔드 A의 함수가 있으면 호출
            process_course_assets(
                course_id=course_id,
                instructor_id=instructor_id,
                video_path=video_path,
                audio_path=audio_path,
                pdf_path=pdf_path,
            )
            logger.info(f"Course {course_id} processed successfully via backend A processor")
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
            )
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Error processing course {course_id}: {error_msg}", exc_info=True)
        # DB에 실패 상태 및 에러 메시지 저장
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
        
        # 비디오 처리 (STT)
        if video_path:
            try:
                if not video_path.exists():
                    raise FileNotFoundError(f"비디오 파일을 찾을 수 없습니다: {video_path}")
                
                logger.info(f"Transcribing video: {video_path}")
                _update_progress(course_id, 10, "음성 인식(STT) 시작")
                
                # OPENAI_API_KEY 확인
                if not settings.openai_api_key:
                    raise ValueError("OPENAI_API_KEY가 설정되지 않았습니다. .env 파일에 OPENAI_API_KEY를 추가하세요.")
                
                transcript_result = transcribe_video(str(video_path), settings=settings)
                _update_progress(course_id, 40, "음성 인식(STT) 완료")
                transcript_text = transcript_result.get("text", "")
                segments = transcript_result.get("segments", [])
                
                # STT placeholder 체크
                if "placeholder" in transcript_text.lower() or not transcript_text.strip():
                    raise ValueError(
                        "STT 처리가 실패했습니다. OPENAI_API_KEY가 설정되어 있는지 확인하세요. "
                        "또는 파일 형식이 지원되지 않을 수 있습니다."
                    )
                
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
                
                vid = Video(
                    course_id=course_id,
                    filename=video_path.name,
                    storage_path=str(video_path),
                    filetype=file_type,
                )
                session.add(vid)
                session.commit()
                logger.info(f"Video record created: {video_path.name}")
                
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
                logger.info(f"Transcribing audio: {audio_path}")
                _update_progress(course_id, 10, "오디오 음성 인식(STT) 시작")
                transcript_result = transcribe_video(str(audio_path), settings=settings)
                _update_progress(course_id, 40, "오디오 음성 인식(STT) 완료")
                transcript_text = transcript_result.get("text", "")
                segments = transcript_result.get("segments", [])
                
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
                
                # Audio 레코드 생성
                audio_file = Video(
                    course_id=course_id,
                    filename=audio_path.name,
                    storage_path=str(audio_path),
                    filetype="audio",
                )
                session.add(audio_file)
                session.commit()
                logger.info(f"Audio record created: {audio_path.name}")
                
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
                
                doc = Video(
                    course_id=course_id,
                    filename=pdf_path.name,
                    storage_path=str(pdf_path),
                    filetype="pdf",
                )
                session.add(doc)
                session.commit()
                logger.info(f"PDF record created: {pdf_path.name}")
            except Exception as e:
                logger.error(f"PDF processing error: {e}", exc_info=True)
        
        # 전체 텍스트 임베딩 및 벡터 DB 저장 (세그먼트는 이미 저장됨)
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
                session.commit()
                raise Exception(error_msg)
        
        # 처리 완료
        course = session.get(Course, course_id)
        if course:
            course.status = CourseStatus.completed
            course.progress = 100
            course.updated_at = datetime.utcnow()
            session.commit()
            logger.info(f"Course {course_id} processing completed successfully")

