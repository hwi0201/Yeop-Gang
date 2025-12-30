from pathlib import Path
from typing import Any

from ai.config import AISettings


def get_chroma_client(settings: AISettings) -> "chromadb.ClientAPI":
    """Initialize or reuse a persistent Chroma client."""
    import chromadb  # Lazy import to avoid native extension issues at module import time

    Path(settings.chroma_db_path).mkdir(parents=True, exist_ok=True)
    return chromadb.PersistentClient(path=settings.chroma_db_path)


def get_collection(client: "chromadb.ClientAPI", name: str = "courses") -> Any:
    """Return a collection for course-scoped embeddings."""
    return client.get_or_create_collection(name=name)

