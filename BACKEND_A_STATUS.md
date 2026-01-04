# 백엔드 A (AI Engine) 역할 및 구현 현황

## 🎯 백엔드 A의 핵심 역할

**당신(백엔드 A)은 `server/ai/` 폴더 전체를 담당합니다.**

### 담당 영역
1. **STT (Speech-to-Text)**: 비디오 → 텍스트 변환
2. **RAG 파이프라인**: 벡터 검색 + LLM 답변 생성
3. **페르소나 추출**: 강사 말투 학습 및 적용
4. **임베딩 생성**: 텍스트 → 벡터 변환
5. **벡터스토어 관리**: ChromaDB 연동

### 작업 범위
- ✅ **`server/ai/` 폴더만 작업** (다른 폴더는 백엔드 B가 담당)
- ✅ API 엔드포인트는 백엔드 B가 관리 (`server/api/routers.py`)
- ✅ DB 스키마는 백엔드 B가 관리 (`server/core/models.py`)
- ✅ 당신은 **AI 로직**만 집중하면 됨

---

## ✅ 현재 구현 상태

### 1. STT (Speech-to-Text) - **완료 ✅**
**파일**: `server/ai/services/stt.py`

- ✅ OpenAI Whisper API 연동 완료
- ✅ 타임스탬프(segments) 추출 완료
- ⚠️ API key가 없으면 placeholder 반환 (정상 동작)

**상태**: **실제 동작 가능** (OPENAI_API_KEY만 있으면 됨)

---

### 2. RAG 파이프라인 - **완료 ✅**
**파일**: `server/ai/pipelines/rag.py`

- ✅ `ingest_texts()`: 텍스트 → 임베딩 → ChromaDB 저장 완료
- ✅ `query()`: 벡터 검색 + LLM 답변 생성 완료
- ✅ `course_id` 기반 필터링 완료
- ✅ 메타데이터 (start_time, end_time) 저장/반환 완료
- ⚠️ API key가 없으면 placeholder 반환 (정상 동작)

**상태**: **실제 동작 가능** (OPENAI_API_KEY만 있으면 됨)

---

### 3. 임베딩 생성 - **완료 ✅**
**파일**: `server/ai/services/embeddings.py`

- ✅ OpenAI Embeddings API 연동 완료
- ✅ 배치 처리 지원

**상태**: **완전 구현됨**

---

### 4. 벡터스토어 관리 - **완료 ✅**
**파일**: `server/ai/services/vectorstore.py`

- ✅ ChromaDB 클라이언트 초기화
- ✅ 컬렉션 관리 (embedding 모델별 분리)
- ✅ 차원 불일치 자동 처리

**상태**: **완전 구현됨**

---

### 5. 페르소나 추출 - **부분 구현 ⚠️**
**파일**: `server/ai/pipelines/rag.py`의 `generate_persona_prompt()`

- ⚠️ 현재: 매우 간단한 스텁만 있음
  - 샘플 텍스트 앞 500자만 사용
  - 실제 스타일 분석 로직 없음

**해야 할 일**:
- 강사 말투 패턴 분석 (종결어미, 어투, 습관적 표현)
- 샘플 텍스트에서 특징 추출
- LLM 프롬프트로 스타일 설명 생성

**상태**: **기본 구조만 있음, 개선 필요**

---

### 6. PDF/이미지 처리 - **미구현 ❌**
- 멀티모달 (VLM) 처리 필요
- 현재는 PDF placeholder만 있음

**상태**: **Phase 2 작업 (후순위)**

---

## 📋 다음에 해야 할 작업 (우선순위)

### 🚨 긴급 (지금 바로)
1. **환경 설정 완료**
   - `.env`에 `OPENAI_API_KEY` 설정 확인
   - 패키지 설치 완료 (`pip install -r requirements.txt`)
   - ⚠️ `tiktoken` 빌드 오류는 **별개 문제** (의존성 설치 이슈)
     - 해결: Rust 설치 또는 `tiktoken` 제외 (임시)

### ⭐ 높은 우선순위
2. **페르소나 추출 알고리즘 개선**
   - `generate_persona_prompt()` 함수 개선
   - 샘플 텍스트 분석 → 스타일 패턴 추출
   - LLM을 활용한 페르소나 프롬프트 생성

3. **테스트 및 검증**
   - 실제 비디오 업로드 → STT → RAG 질의 플로우 테스트
   - 답변 품질 확인
   - 타임스탬프 링크 작동 확인

### 🔄 중간 우선순위
4. **RAG 답변 품질 개선**
   - 컨텍스트 길이 최적화
   - 소스 인용 형식 개선
   - 답변 스타일 일관성 유지

5. **에러 핸들링 강화**
   - API 호출 실패 시 재시도 로직
   - 타임아웃 처리

### ⏭️ 낮은 우선순위 (Phase 2)
6. **PDF/이미지 처리**
   - VLM (Vision-Language Model) 연동
   - 도표/그림 텍스트 추출

---

## 🧪 테스트 방법

### 1. 단위 테스트 (개별 함수)
```bash
cd server
source ../.venv/bin/activate

# STT 테스트
python -c "from ai.services.stt import transcribe_video; from ai.config import AISettings; print(transcribe_video('video/testvedio_1.mp4', AISettings()))"

# RAG 테스트
python -c "from ai.pipelines.rag import RAGPipeline; from ai.config import AISettings; p = RAGPipeline(AISettings()); print(p.query('안녕하세요', course_id='test-course-1'))"
```

### 2. 통합 테스트 (전체 플로우)
```bash
# 1. 서버 실행
cd server
source ../.venv/bin/activate
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000

# 2. 비디오 업로드
curl -X POST "http://localhost:8000/api/upload" \
  -F "instructor_id=test-1" \
  -F "course_id=test-course-1" \
  -F "video=@/Users/mac/Desktop/hateslop/Yeop-Gang/video/testvedio_1.mp4"

# 3. 상태 확인 (처리 완료 대기)
curl http://localhost:8000/api/status/test-course-1

# 4. 채팅 질의
curl -X POST "http://localhost:8000/api/chat/ask" \
  -H "Content-Type: application/json" \
  -d '{"course_id": "test-course-1", "question": "이 강의에서 무엇을 배우나요?", "session_id": "test-1"}'
```

---

## 🚨 주의사항

### 1. `tiktoken` 빌드 오류
- **문제**: Rust 컴파일러 필요
- **해결 옵션 A (빠름)**: `tiktoken` 없이 진행 (현재 코드에서 필수 아님)
- **해결 옵션 B (완전)**: Rust 설치
  ```bash
  curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
  source "$HOME/.cargo/env"
  pip install -r requirements.txt
  ```

### 2. API Key 설정
- `.env` 파일에 `OPENAI_API_KEY=sk-...` 설정 필수
- 서버 재시작 후 적용

### 3. 작업 범위
- **`server/ai/` 폴더만 수정**
- 다른 폴더 수정 시 백엔드 B와 협의

---

## 📞 백엔드 B와의 협업 포인트

### 백엔드 B가 당신을 호출하는 방식
```python
# server/core/tasks.py에서
from ai.services.stt import transcribe_video  # STT 호출
from ai.pipelines.rag import RAGPipeline      # RAG 파이프라인 호출

# 백엔드 B가 업로드 → 배경 작업에서 당신의 함수 호출
```

### 당신이 제공하는 인터페이스
- ✅ `transcribe_video(video_path, settings)` → STT 결과
- ✅ `RAGPipeline.ingest_texts()` → 벡터 DB 저장
- ✅ `RAGPipeline.query()` → RAG 검색 + 답변
- ✅ `RAGPipeline.generate_persona_prompt()` → 페르소나 프롬프트

**이 인터페이스는 이미 구현되어 있고, 백엔드 B가 사용 중입니다.**

---

## ✅ 요약

### 현재 상태
- ✅ **STT, RAG, 임베딩, 벡터스토어: 모두 구현 완료**
- ⚠️ **페르소나 추출: 기본 구조만, 개선 필요**
- ❌ **PDF/이미지: 미구현 (Phase 2)**

### 지금 해야 할 일
1. 환경 설정 완료 (`.env` 설정, 패키지 설치)
2. 실제 테스트 (비디오 업로드 → 질의 플로우)
3. 페르소나 추출 알고리즘 개선

**핵심**: 코드는 거의 다 구현되어 있습니다. 이제 **테스트하고 개선**하는 단계입니다! 🚀

