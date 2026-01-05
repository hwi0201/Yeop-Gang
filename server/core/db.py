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


def _migrate_add_progress_column() -> None:
    """Course 테이블에 progress 컬럼 추가 (마이그레이션)"""
    try:
        from sqlalchemy import inspect, text
        
        # SQLite인지 확인
        if engine.dialect.name != "sqlite":
            return
        
        # 테이블이 존재하는지 확인
        inspector = inspect(engine)
        if "course" not in inspector.get_table_names():
            return
        
        # progress 컬럼이 이미 있는지 확인
        columns = [col["name"] for col in inspector.get_columns("course")]
        if "progress" in columns:
            return
        
        # ALTER TABLE 실행 (autocommit 모드)
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE course ADD COLUMN progress INTEGER DEFAULT 0"))
    except Exception as e:
        # 마이그레이션 실패해도 계속 진행 (컬럼이 이미 있을 수 있음)
        import logging
        logger = logging.getLogger(__name__)
        logger.debug(f"Progress column migration: {e}")


def init_db() -> None:
    """Create tables if they do not exist."""
    SQLModel.metadata.create_all(engine)
    # 기존 테이블에 progress 컬럼 추가 (마이그레이션)
    _migrate_add_progress_column()


def get_session() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session

