from typing import Iterable, List

from ai.config import AISettings


def embed_texts(texts: Iterable[str], settings: AISettings) -> List[List[float]]:
    """Generate embeddings via OpenAI embeddings API."""
    from openai import OpenAI
    from openai import RateLimitError, APIError

    if not settings.openai_api_key:
        raise ValueError("OPENAI_API_KEY가 설정되지 않았습니다.")
    
    client = OpenAI(api_key=settings.openai_api_key)
    
    try:
        # OpenAI embeddings API supports batching; send as one request
        resp = client.embeddings.create(
            input=list(texts),
            model=settings.embedding_model,
        )
        return [item.embedding for item in resp.data]
    except RateLimitError as e:
        error_msg = str(e)
        if "insufficient_quota" in error_msg or "quota" in error_msg.lower():
            raise ValueError(
                "OpenAI API 할당량이 초과되었습니다. "
                "OpenAI 계정의 크레딧을 확인하거나 결제 정보를 업데이트하세요. "
                "https://platform.openai.com/account/billing"
            )
        else:
            raise ValueError(
                f"OpenAI API Rate Limit 초과: {error_msg}. 잠시 후 다시 시도하세요."
            )
    except APIError as e:
        raise ValueError(f"OpenAI API 오류: {str(e)}")

