from pathlib import Path
from typing import Any, Optional

from ai.config import AISettings


def get_chroma_client(settings: AISettings) -> "chromadb.ClientAPI":
    """Initialize or reuse a persistent Chroma client."""
    import chromadb  # Lazy import to avoid native extension issues at module import time

    Path(settings.chroma_db_path).mkdir(parents=True, exist_ok=True)
    return chromadb.PersistentClient(path=settings.chroma_db_path)


def get_collection(
    client: "chromadb.ClientAPI",
    settings: AISettings,
    name: Optional[str] = None,
) -> Any:
    """
    Return a collection for course-scoped embeddings.
    Use embedding_model suffix to avoid dimension mismatch across models.
    """
    coll_name = name or f"courses-{settings.embedding_model}"
    return client.get_or_create_collection(name=coll_name)

