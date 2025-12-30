import os
from dataclasses import dataclass


@dataclass
class AISettings:
    """AI-related environment configuration."""

    openai_api_key: str | None = os.getenv("OPENAI_API_KEY")
    google_api_key: str | None = os.getenv("GOOGLE_API_KEY")
    chroma_db_path: str = os.getenv("CHROMA_DB_PATH", "data/chroma")
    llm_model: str = os.getenv("LLM_MODEL", "gpt-4o-mini")
    embedding_model: str = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")

