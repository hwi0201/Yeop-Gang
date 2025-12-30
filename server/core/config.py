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
        return Path(self.data_root) / "uploads"

