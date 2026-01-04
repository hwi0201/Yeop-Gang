from pathlib import Path
from typing import Optional

from fastapi import BackgroundTasks
from sqlmodel import Session

from ai.config import AISettings
from ai.pipelines.rag import RAGPipeline
from ai.services.stt import transcribe_video
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

    with Session(engine) as session:
        course = session.get(Course, course_id)
        if not course:
            course = Course(id=course_id, instructor_id=instructor_id)
            session.add(course)
        course.status = CourseStatus.processing
        session.commit()

        texts: list[str] = []
        if video_path:
            transcript_result = transcribe_video(str(video_path), settings=settings)
            transcript_text = transcript_result.get("text", "")
            segments = transcript_result.get("segments", [])
            if transcript_text:
                # 병합 텍스트 전체를 하나의 문서로 저장
                texts.append(transcript_text)
                # 세그먼트별 메타데이터 포함하여 추가 저장
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
            vid = Video(
                course_id=course_id,
                filename=video_path.name,
                storage_path=str(video_path),
                filetype="video",
            )
            session.add(vid)
        if pdf_path:
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

        if texts:
            pipeline.ingest_texts(
                texts,
                course_id=course_id,
                metadata={"course_id": course_id, "instructor_id": instructor_id},
            )
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

        course.status = CourseStatus.completed
        session.commit()

