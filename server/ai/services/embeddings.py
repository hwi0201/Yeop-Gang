from typing import Iterable, List

from ai.config import AISettings


def embed_texts(texts: Iterable[str], settings: AISettings) -> List[List[float]]:
    """Generate embeddings via OpenAI embeddings API."""
    from openai import OpenAI

    client = OpenAI(api_key=settings.openai_api_key)
    # OpenAI embeddings API supports batching; send as one request
    resp = client.embeddings.create(
        input=list(texts),
        model=settings.embedding_model,
    )
    return [item.embedding for item in resp.data]

