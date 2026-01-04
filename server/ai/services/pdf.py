"""
백엔드 A: PDF 멀티모달 처리 서비스
- PDF 텍스트 추출
- PDF 이미지/도표/그림 추출 및 Vision API로 설명 생성
- 텍스트와 이미지 설명 결합
"""
from pathlib import Path
from typing import Dict, List, Any, Optional
import base64

from ai.config import AISettings

try:
    import fitz  # PyMuPDF
except ImportError:
    fitz = None  # type: ignore

try:
    from openai import OpenAI
except Exception:
    OpenAI = None  # type: ignore


def _openai_client(settings: AISettings):
    """OpenAI 클라이언트 생성 (Vision API용)"""
    if not settings.openai_api_key:
        raise RuntimeError("OPENAI_API_KEY is not set")
    return OpenAI(api_key=settings.openai_api_key)


def describe_image_with_vision(
    image_bytes: bytes,
    settings: AISettings,
    page_num: int,
    context: Optional[str] = None
) -> str:
    """
    OpenAI Vision API를 사용하여 이미지(도표/그림) 설명 생성
    
    Args:
        image_bytes: 이미지 바이트 데이터
        settings: AISettings 인스턴스
        page_num: PDF 페이지 번호 (컨텍스트용)
        context: 이미지 주변 텍스트 (선택적)
    
    Returns:
        이미지에 대한 설명 텍스트
    """
    if OpenAI is None or not settings.openai_api_key:
        return f"[페이지 {page_num}의 이미지/도표 - Vision API를 사용할 수 없어 설명을 생성할 수 없습니다]"
    
    try:
        client = _openai_client(settings)
        
        # 이미지를 base64로 인코딩
        image_base64 = base64.b64encode(image_bytes).decode('utf-8')
        
        # 프롬프트 구성
        prompt = (
            "이 이미지는 강의 자료의 PDF에서 추출된 도표, 그래프, 또는 그림입니다. "
            "이미지의 내용을 자세히 설명해주세요. 특히:\n"
            "- 도표/그래프인 경우: 축 레이블, 데이터 값, 범례, 트렌드\n"
            "- 그림/다이어그램인 경우: 요소들 간의 관계, 주요 특징\n"
            "- 수식이나 텍스트가 있는 경우: 그 내용\n"
            "한국어로 상세하고 정확하게 설명해주세요."
        )
        
        if context:
            prompt += f"\n\n참고: 이 이미지 주변의 텍스트 컨텍스트:\n{context[:500]}"
        
        response = client.chat.completions.create(
            model="gpt-4o",  # Vision API 지원 모델
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": prompt,
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{image_base64}",
                            },
                        },
                    ],
                }
            ],
            max_tokens=500,
            temperature=0.3,
        )
        
        description = response.choices[0].message.content
        return f"[페이지 {page_num} 이미지 설명: {description}]"
        
    except Exception as e:
        error_msg = str(e)
        print(f"Vision API 오류 (페이지 {page_num}): {error_msg}")
        return f"[페이지 {page_num}의 이미지/도표 - 설명 생성 실패: {error_msg}]"


def extract_pdf_content(
    pdf_path: str | Path,
    settings: AISettings,
    extract_images: bool = True,
) -> Dict[str, Any]:
    """
    PDF에서 텍스트와 이미지를 추출하고, 이미지는 Vision API로 설명 생성
    
    Args:
        pdf_path: PDF 파일 경로
        settings: AISettings 인스턴스
        extract_images: 이미지 추출 및 설명 생성 여부 (기본: True)
    
    Returns:
        {
            "texts": List[str],  # 페이지별 텍스트 + 이미지 설명
            "metadata": List[Dict],  # 각 텍스트에 대한 메타데이터
        }
    """
    if fitz is None:
        raise ImportError(
            "PyMuPDF (fitz)가 설치되지 않았습니다. "
            "pip install pymupdf로 설치해주세요."
        )
    
    path = Path(pdf_path)
    if not path.exists():
        raise FileNotFoundError(f"PDF 파일을 찾을 수 없습니다: {pdf_path}")
    
    doc = fitz.open(path)
    all_texts: List[str] = []
    all_metadata: List[Dict[str, Any]] = []
    
    try:
        for page_num in range(len(doc)):
            page = doc[page_num]
            
            # 1. 텍스트 추출
            page_text = page.get_text("text").strip()
            
            # 2. 이미지 추출 (선택적)
            image_descriptions: List[str] = []
            if extract_images and OpenAI is not None and settings.openai_api_key:
                image_list = page.get_images(full=True)
                
                # 이미지 주변 텍스트를 컨텍스트로 사용
                context_text = page_text[:1000] if page_text else ""  # 간단한 컨텍스트
                
                for img_idx, img_info in enumerate(image_list):
                    try:
                        xref = img_info[0]
                        base_image = doc.extract_image(xref)
                        image_bytes = base_image["image"]
                        
                        # 이미지 설명 생성
                        description = describe_image_with_vision(
                            image_bytes=image_bytes,
                            settings=settings,
                            page_num=page_num + 1,  # 1-based 페이지 번호
                            context=context_text,
                        )
                        image_descriptions.append(description)
                        
                    except Exception as e:
                        print(f"이미지 추출 오류 (페이지 {page_num + 1}, 이미지 {img_idx + 1}): {e}")
                        continue
            
            # 3. 텍스트와 이미지 설명을 결합
            if page_text or image_descriptions:
                combined_text = page_text
                if image_descriptions:
                    combined_text += "\n\n" + "\n\n".join(image_descriptions)
                
                all_texts.append(combined_text)
                all_metadata.append({
                    "source": path.name,
                    "page_number": page_num + 1,  # 1-based
                    "type": "pdf_page",
                })
        
        return {
            "texts": all_texts,
            "metadata": all_metadata,
        }
        
    finally:
        doc.close()

