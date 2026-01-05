# 백엔드 A 남은 구현 작업

## ✅ 이미 구현 완료된 기능

### 1. 자동화 STT & 전처리 (`server/ai/services/stt.py`)
- ✅ OpenAI Whisper API 연동
- ✅ 영상/오디오 파일에서 텍스트 추출
- ✅ 타임스탬프(시작/종료 시간) 추출
- ✅ 대용량 파일 분할 처리 (25MB 이상 파일 처리)

### 2. 멀티모달 RAG 설계 (`server/ai/services/pdf.py`) ✅ 방금 완료
- ✅ PDF 텍스트 추출 (PyMuPDF)
- ✅ PDF 이미지/도표/그림 추출
- ✅ OpenAI Vision API를 사용한 이미지 설명 생성
- ✅ 텍스트와 이미지 설명을 결합
- ✅ 페이지별 메타데이터 관리

### 3. 동적 페르소나 추출 (`server/ai/pipelines/rag.py`의 `generate_persona_prompt`)
- ✅ LLM을 사용한 말투 분석 (종결어미, 어투, 표현 패턴 등)
- ✅ 분석 결과를 System Prompt로 변환
- ✅ 페르소나 프롬프트를 벡터 DB에 저장

### 4. RAG 파이프라인 (`server/ai/pipelines/rag.py`)
- ✅ `ingest_texts()`: 텍스트 임베딩 및 벡터 DB 저장
- ✅ `query()`: course_id 필터링을 통한 하이브리드 검색
- ✅ LLM을 통한 답변 생성 (강의 컨텍스트 우선)
- ✅ 대화 히스토리 지원

---

## ❌ 아직 구현되지 않은 기능

### 1. 파이프라인 오케스트레이션 (`server/ai/pipelines/processor.py` - 새로 생성 필요)

**목표:** STT → PDF 처리 → 페르소나 추출 → RAG 인제스트 전체 흐름 관리

**현재 상태:**
- ❌ 파일이 아직 없음
- ⚠️ `server/core/tasks.py`에 `process_course_assets()` 함수가 있지만, 이는 백엔드 B 영역
- 백엔드 A가 `server/ai/pipelines/processor.py`에 자신만의 버전을 만들어야 함

**구현해야 할 내용:**
```python
# server/ai/pipelines/processor.py
def process_course_assets(
    *,
    course_id: str,
    instructor_id: str,
    video_path: Optional[Path],
    pdf_path: Optional[Path],
) -> None:
    """
    백엔드 A: 자동화 파이프라인 오케스트레이션
    STT → PDF 처리 → 페르소나 추출 → RAG 인제스트
    """
    # 1. STT 처리 (video_path가 있으면)
    # 2. PDF 처리 (pdf_path가 있으면)
    # 3. 페르소나 추출
    # 4. RAG 인제스트 (텍스트, 이미지 설명, 페르소나 모두)
```

**주의사항:**
- DB 관련 코드 (Course, Video 모델 생성 등)는 백엔드 B의 책임
- 백엔드 A는 **순수 AI 처리 로직**만 담당
- DB 작업이 필요하면 백엔드 B의 함수를 호출하거나, 파라미터로 받아야 함

---

### 2. 실시간 스트리밍 질의응답 (선택사항)

**목표:** 1~2초 내 즉각 답변 생성 및 스트리밍 출력

**현재 상태:**
- ✅ 빠른 답변 생성은 이미 구현됨 (`rag.py`의 `query()`)
- ❌ 스트리밍 출력 (SSE/WebSocket) - 백엔드 B와 협업 필요

**구현 방법:**
- `query()` 메서드를 Generator로 변경하여 토큰 단위로 스트리밍
- 또는 백엔드 B가 SSE/WebSocket 엔드포인트를 만들고, 백엔드 A가 스트리밍 함수 제공

**우선순위:** 낮음 (백엔드 B와 협업 필요)

---

## 📝 구현 우선순위

### 🔥 최우선 (즉시 구현 필요)

1. **파이프라인 오케스트레이션** (`server/ai/pipelines/processor.py`)
   - 이유: 백엔드 B가 이 함수를 호출할 예정
   - 현재 `server/core/tasks.py`에 있는 로직을 참고하되, DB 작업 제외
   - STT + PDF 처리 + 페르소나 + RAG 인제스트 통합

### ⚠️ 선택사항 (나중에 구현 가능)

2. **스트리밍 질의응답**
   - 백엔드 B와 협업 필요
   - 현재 기본 질의응답은 이미 작동함

3. **검색 최적화**
   - 하이브리드 검색 고도화
   - RAG 파이프라인 개선

---

## 🎯 다음 단계 제안

1. `server/ai/pipelines/processor.py` 생성
2. STT, PDF, 페르소나, RAG 인제스트 로직 통합
3. DB 작업은 제외 (백엔드 B의 책임)
4. 백엔드 B와 인터페이스 확인

