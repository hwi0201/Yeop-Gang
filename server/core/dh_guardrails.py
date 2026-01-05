"""
AI 답변 가드레일 (Guardrails)
- 윤리 가이드라인 적용
- 부적절한 콘텐츠 필터링
- 답변 품질 검증
"""
import re
from typing import Optional


class Guardrails:
    """AI 답변 가드레일 클래스"""
    
    # 금지된 키워드 목록 (예시)
    FORBIDDEN_KEYWORDS = [
        "폭력", "혐오", "차별", "불법", "마약", "도박",
        # 추가 금지 키워드 확장 가능
    ]
    
    # 민감한 주제 키워드
    SENSITIVE_TOPICS = [
        "정치", "종교", "성", "인종",
    ]
    
    def __init__(self):
        self.forbidden_pattern = re.compile(
            "|".join(self.FORBIDDEN_KEYWORDS),
            re.IGNORECASE
        )
    
    def check_content(self, text: str) -> tuple[bool, Optional[str]]:
        """
        콘텐츠 검증
        Returns: (is_safe, reason)
        """
        if not text or len(text.strip()) == 0:
            return False, "Empty content"
        
        # 금지 키워드 확인
        if self.forbidden_pattern.search(text):
            return False, "Contains forbidden keywords"
        
        # 너무 짧은 답변 (품질 검증)
        if len(text.strip()) < 10:
            return False, "Answer too short"
        
        # 너무 긴 답변 (비정상적)
        if len(text) > 10000:
            return False, "Answer too long"
        
        return True, None
    
    def filter_response(self, response: str) -> str:
        """
        응답 필터링 및 정제
        """
        # 기본 정제
        filtered = response.strip()
        
        # 연속된 공백 제거
        filtered = re.sub(r'\s+', ' ', filtered)
        
        # 금지 키워드가 포함된 경우 마스킹
        if self.forbidden_pattern.search(filtered):
            filtered = self.forbidden_pattern.sub("[필터링됨]", filtered)
        
        return filtered
    
    def validate_educational_content(self, text: str) -> tuple[bool, Optional[str]]:
        """
        교육적 콘텐츠 검증
        """
        # 교육 관련 키워드 확인 (선택적)
        educational_keywords = ["학습", "교육", "강의", "설명", "예시", "문제"]
        has_educational_content = any(
            keyword in text for keyword in educational_keywords
        )
        
        # 필수는 아니지만, 교육적 콘텐츠가 있으면 더 좋음
        return True, None


# 전역 Guardrails 인스턴스
guardrails = Guardrails()


def apply_guardrails(response: str) -> tuple[str, bool]:
    """
    가드레일 적용
    Returns: (filtered_response, is_safe)
    """
    is_safe, reason = guardrails.check_content(response)
    
    if not is_safe:
        # 안전하지 않은 경우 기본 메시지 반환
        return "죄송합니다. 적절한 답변을 생성할 수 없습니다.", False
    
    # 필터링 적용
    filtered = guardrails.filter_response(response)
    
    return filtered, True

