from typing import Iterable, List

from ai.config import AISettings

try:
    from openai import OpenAI
    from openai import RateLimitError, APIError
except Exception:
    OpenAI = None  # type: ignore
    RateLimitError = None  # type: ignore
    APIError = None  # type: ignore


def embed_texts(texts: Iterable[str], settings: AISettings) -> List[List[float]]:
    """
    Generate embeddings via OpenAI embeddings API.
    
    Raises:
        RuntimeError: If OpenAI client is not available or API key is missing
        ValueError: If API quota is exceeded or other API errors occur
    """
    if OpenAI is None or not settings.openai_api_key:
        raise RuntimeError("OpenAI client not available or API key is missing")
    
    client = OpenAI(api_key=settings.openai_api_key)
    
    try:
        # OpenAI embeddings API supports batching; send as one request
        resp = client.embeddings.create(
            input=list(texts),
            model=settings.embedding_model,
        )
        return [item.embedding for item in resp.data]
    except RateLimitError as e:
        error_msg = (
            "OpenAI API 할당량을 초과했습니다. "
            "계정의 결제 정보와 사용 한도를 확인해주세요. "
            f"에러 코드: {e.status_code if hasattr(e, 'status_code') else '429'}"
        )
        print(f"ERROR [Embeddings]: {error_msg}")
        raise ValueError(error_msg) from e
    except APIError as e:
        error_msg = f"OpenAI API 오류가 발생했습니다: {str(e)}"
        print(f"ERROR [Embeddings]: {error_msg}")
        raise ValueError(error_msg) from e

