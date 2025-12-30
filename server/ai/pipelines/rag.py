from typing import Iterable, Optional

from ai.config import AISettings
from ai.services.vectorstore import get_chroma_client, get_collection


class RAGPipeline:
    """
    Minimal RAG pipeline scaffold.
    Backend A can extend methods to add embeddings, retrievers, and LLM calls.
    """

    def __init__(self, settings: AISettings):
        self.settings = settings
        self.client = get_chroma_client(settings)
        self.collection = get_collection(self.client)

    def ingest_texts(
        self,
        texts: Iterable[str],
        *,
        course_id: str,
        metadata: Optional[dict] = None,
    ) -> dict:
        """Stub ingestion; metadata always includes course_id for isolation."""
        entries = list(texts)
        if not entries:
            return {"ingested": 0}

        md = metadata or {}
        for item in entries:
            md.setdefault("course_id", course_id)

        self.collection.upsert(
            ids=[f"{course_id}-doc-{i}" for i, _ in enumerate(entries)],
            documents=entries,
            metadatas=[{**md, "course_id": course_id} for _ in entries],
        )
        return {"ingested": len(entries)}

    def query(self, question: str, *, course_id: str) -> dict:
        """
        Stub retrieval with course_id filter; extend with hybrid search + LLM synthesis.
        """
        results = self.collection.query(
            query_texts=[question],
            n_results=3,
            include=["documents", "ids", "metadatas"],
            where={"course_id": course_id},
        )
        return {
            "question": question,
            "documents": results.get("documents", []),
            "ids": results.get("ids", []),
            "metadatas": results.get("metadatas", []),
            "answer": "LLM synthesis placeholder. Connect to GPT-4o/Gemini.",
        }

    def generate_persona_prompt(
        self, *, course_id: str, sample_texts: list[str]
    ) -> str:
        """
        Simple persona stub: derives tone from sample texts.
        Extend with actual stylistic analysis.
        """
        sample = sample_texts[0][:500] if sample_texts else ""
        return (
            f"당신은 course_id={course_id} 강사의 말투를 모방한 AI입니다. "
            f"아래 샘플을 참고하여 답변하세요:\n{sample}"
        )

