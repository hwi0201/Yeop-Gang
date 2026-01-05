# dh: 이 파일은 백엔드 B의 Task 관리용입니다.
# dh: 실제 처리 로직은 백엔드 A의 ai/pipelines/processor.py로 이동되었습니다.
# dh: 이 파일은 호환성을 위해 유지되지만, 새로운 코드는 server/core/dh_tasks.py를 사용하세요.

from pathlib import Path
from typing import Optional

from fastapi import BackgroundTasks

# dh: 새로운 Task 관리 모듈 사용
from core.dh_tasks import enqueue_processing_task as _enqueue_processing_task


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
    dh: 내부적으로 core.dh_tasks.enqueue_processing_task()를 호출합니다.
    """
    _enqueue_processing_task(
        tasks,
        course_id=course_id,
        instructor_id=instructor_id,
        video_path=video_path,
        audio_path=audio_path,
        pdf_path=pdf_path,
    )

