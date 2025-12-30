from pathlib import Path
from typing import Optional

from fastapi import UploadFile

from core.config import AppSettings


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def save_upload_file(file: UploadFile, base_dir: Path) -> Path:
    ensure_dir(base_dir)
    target = base_dir / file.filename
    with target.open("wb") as f:
        f.write(file.file.read())
    return target


def save_course_assets(
    instructor_id: str,
    course_id: str,
    video: Optional[UploadFile],
    pdf: Optional[UploadFile],
    settings: Optional[AppSettings] = None,
) -> dict[str, Optional[Path]]:
    settings = settings or AppSettings()
    course_dir = settings.uploads_dir / instructor_id / course_id
    ensure_dir(course_dir)

    paths: dict[str, Optional[Path]] = {"video": None, "pdf": None}
    if video:
        paths["video"] = save_upload_file(video, course_dir)
    if pdf:
        paths["pdf"] = save_upload_file(pdf, course_dir)
    return paths

