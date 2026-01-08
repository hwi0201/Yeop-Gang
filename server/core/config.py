import os
from pathlib import Path
from dataclasses import dataclass


@dataclass
class AppSettings:
    """Global app settings."""

    database_url: str = os.getenv("DATABASE_URL", "sqlite:///./data/yeopgang.db")
    data_root: str = os.getenv("DATA_ROOT", "data")

    @property
    def uploads_dir(self) -> Path:
        """Returns absolute path to uploads directory."""
        base_path = Path(self.data_root)
        # 상대 경로면 server 폴더 기준으로 절대 경로 변환
        if not base_path.is_absolute():
            # server/core/config.py -> server
            server_dir = Path(__file__).resolve().parent.parent
            base_path = server_dir / self.data_root
        return base_path / "uploads"

