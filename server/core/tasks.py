from pathlib import Path
from typing import Optional

from fastapi import BackgroundTasks
from sqlmodel import Session

from ai.config import AISettings
from ai.pipelines.rag import RAGPipeline
from ai.services.stt import transcribe_video
from ai.services.pdf import extract_pdf_content
from core.db import engine
from core.models import Course, CourseStatus, Instructor, Video


def enqueue_processing_task(
    tasks: BackgroundTasks,
    *,
    course_id: str,
    instructor_id: str,
    video_path: Optional[Path],
    pdf_path: Optional[Path],
) -> None:
    tasks.add_task(
        process_course_assets,
        course_id=course_id,
        instructor_id=instructor_id,
        video_path=video_path,
        pdf_path=pdf_path,
    )


def process_course_assets(
    *,
    course_id: str,
    instructor_id: str,
    video_path: Optional[Path],
    pdf_path: Optional[Path],
) -> None:
    """Background pipeline: STT -> persona sample -> vector ingest."""
    settings = AISettings()
    pipeline = RAGPipeline(settings)

    try:
        with Session(engine) as session:
            course = session.get(Course, course_id)
            if not course:
                course = Course(id=course_id, instructor_id=instructor_id)
                session.add(course)
            course.status = CourseStatus.processing
            session.commit()

            texts: list[str] = []
            if video_path:
                print(f"[{course_id}] STT 처리 시작: {video_path.name}")
                transcript_result = transcribe_video(str(video_path), settings=settings)
                transcript_text = transcript_result.get("text", "")
                segments = transcript_result.get("segments", [])
                if transcript_text:
                    # 병합 텍스트 전체를 하나의 문서로 저장
                    texts.append(transcript_text)
                    # 세그먼트별 메타데이터 포함하여 추가 저장
                    print(f"[{course_id}] {len(segments)}개 세그먼트 인제스트 시작...")
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
                        }
                        pipeline.ingest_texts(
                            [seg_text],
                            course_id=course_id,
                            metadata=seg_meta,
                        )
                    print(f"[{course_id}] 세그먼트 인제스트 완료")
                vid = Video(
                    course_id=course_id,
                    filename=video_path.name,
                    storage_path=str(video_path),
                    filetype="video",
                )
                session.add(vid)
            if pdf_path:
                print(f"[{course_id}] PDF 멀티모달 처리 시작: {pdf_path.name}")
                try:
                    pdf_result = extract_pdf_content(str(pdf_path), settings=settings, extract_images=True)
                    pdf_texts = pdf_result.get("texts", [])
                    pdf_metadata_list = pdf_result.get("metadata", [])
                    
                    if pdf_texts:
                        # PDF 텍스트를 페르소나 추출용으로 추가
                        texts.extend(pdf_texts)
                        
                        # 페이지별 RAG 인제스트
                        print(f"[{course_id}] PDF {len(pdf_texts)}개 페이지 인제스트 시작...")
                        for pdf_text, pdf_meta in zip(pdf_texts, pdf_metadata_list):
                            page_meta = {
                                "course_id": course_id,
                                "instructor_id": instructor_id,
                                "source": pdf_path.name,
                                "page_number": pdf_meta.get("page_number"),
                                "type": "pdf_page",
                            }
                            pipeline.ingest_texts(
                                [pdf_text],
                                course_id=course_id,
                                metadata=page_meta,
                            )
                        print(f"[{course_id}] PDF 페이지 인제스트 완료")
                    else:
                        print(f"[{course_id}] ⚠️ PDF에서 텍스트를 추출하지 못했습니다: {pdf_path.name}")
                        
                except Exception as e:
                    print(f"[{course_id}] ❌ PDF 처리 오류 ({pdf_path.name}): {type(e).__name__}: {e}")
                    import traceback
                    traceback.print_exc()
                
                doc = Video(
                    course_id=course_id,
                    filename=pdf_path.name,
                    storage_path=str(pdf_path),
                    filetype="pdf",
                )
                session.add(doc)

            session.commit()

            if texts:
                print(f"[{course_id}] 페르소나 추출 시작...")
                # 페르소나 추출 (전체 텍스트는 페르소나 생성에만 사용, 인제스트는 안 함)
                # 세그먼트별로 이미 인제스트했으므로 전체 텍스트를 다시 인제스트할 필요 없음
                persona_prompt = pipeline.generate_persona_prompt(
                    course_id=course_id, sample_texts=texts
                )
                pipeline.ingest_texts(
                    [persona_prompt],
                    course_id=course_id,
                    metadata={
                        "course_id": course_id,
                        "instructor_id": instructor_id,
                        "type": "persona",
                    },
                )
                print(f"[{course_id}] 페르소나 인제스트 완료")

            course.status = CourseStatus.completed
            session.commit()
            print(f"[{course_id}] ✅ 처리 완료")
    except Exception as e:
        print(f"[{course_id}] ❌ 처리 오류 발생: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        # 오류 발생 시 상태를 failed로 변경
        try:
            with Session(engine) as session:
                course = session.get(Course, course_id)
                if course:
                    course.status = CourseStatus.failed
                    session.commit()
        except Exception as db_error:
            print(f"[{course_id}] ❌ DB 상태 업데이트 실패: {db_error}")

