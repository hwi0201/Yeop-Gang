from typing import Generator
from pathlib import Path
from urllib.parse import urlparse

from sqlmodel import Session, SQLModel, create_engine

from core.config import AppSettings

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _prepare_sqlite_url(url: str) -> str:
    """Ensure sqlite file path exists and is absolute, fallback to project data/ if permission denied."""
    if not url.startswith("sqlite"):
        return url

    parsed = urlparse(url)
    path = parsed.path
    if path.startswith("///"):
        file_path = Path(path[3:])  # strip leading ///
    else:
        file_path = Path(path)

    if not file_path.is_absolute():
        file_path = PROJECT_ROOT / file_path

    try:
        file_path.parent.mkdir(parents=True, exist_ok=True)
    except (PermissionError, OSError):
        # Read-only or permission-denied: fallback to project-local data directory
        fallback = PROJECT_ROOT / "data" / file_path.name
        fallback.parent.mkdir(parents=True, exist_ok=True)
        file_path = fallback

    return f"sqlite:///{file_path}"


settings = AppSettings()
engine = create_engine(_prepare_sqlite_url(settings.database_url), echo=False, future=True)


def init_db() -> None:
    """Create tables if they do not exist."""
    SQLModel.metadata.create_all(engine)


def get_session() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session

