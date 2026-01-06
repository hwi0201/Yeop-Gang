# 백엔드 A/B 역할 분리 상세 가이드

## 📋 총 6개 기능 요약

### 기능 1: 자동 챗봇 생성 파이프라인
강사가 영상(MP4) 및 자료(PDF) 업로드 시 자동으로 지식 베이스(RAG) 구축

### 기능 2: 동적 페르소나 추출
업로드된 스크립트를 분석하여 강사의 고유 말투와 빈출 표현을 AI가 스스로 학습

### 기능 3: 멀티모달 지식 엔진
교재 내 복잡한 수식, 그래프, 도표 이미지를 텍스트 문맥과 결합하여 학습

### 기능 4: 실시간 스트리밍 질의응답
학생의 질문에 대해 강사의 말투로 1~2초 내 즉각 답변 생성 및 스트리밍 출력

### 기능 5: 영상 타임라인 연동
답변 내용의 근거가 되는 영상의 정확한 지점(Timestamp)으로 이동 기능 제공

### 기능 6: 강사/학생 이원화 UI
(강사) 강의 관리 및 학습 상태 모니터링 / (학생) 인강 수청 및 챗봇 활용

---

## 👤 백엔드 A (AI 엔진 & 자동화 파이프라인) - 강유영

**핵심 목표:** 어떤 데이터가 들어와도 일관된 품질의 지식 베이스와 페르소나를 생성하는 자동화 로직 구축

### 📁 작업 공간
- `server/ai/` 폴더 전체

### 🔧 구현해야 할 구체적 기능

#### 1. 자동화 STT & 전처리 (`server/ai/services/stt.py`)
**목표:** Whisper를 활용하여 업로드된 영상에서 텍스트와 타임스탬프를 추출하는 범용 파이프라인 개발

**구현 내용:**
- ✅ OpenAI Whisper API 연동 (또는 로컬 Whisper 모델)
- ✅ 영상/오디오 파일에서 텍스트 추출
- ✅ 타임스탬프(시작/종료 시간) 추출
- ✅ 대용량 파일 분할 처리 (25MB 이상 파일 처리)
- ✅ 추출된 텍스트와 타임스탬프를 구조화된 형태로 반환

**현재 상태:** ✅ 구현됨 (이미 완료)

---

#### 2. 멀티모달 RAG 설계 (`server/ai/services/pdf.py` - 새로 생성 필요)
**목표:** PDF 내의 도표와 수식을 분석하여 텍스트와 결합하는 Vision-to-Text 엔진 구축

**구현 내용:**
- ❌ PDF에서 텍스트 추출 (PyMuPDF 등 사용)
- ❌ PDF에서 이미지/도표/그림 추출
- ❌ OpenAI Vision API를 사용한 이미지 설명 생성
- ❌ 텍스트와 이미지 설명을 결합하여 RAG 인제스트 가능한 형태로 변환
- ❌ 페이지별 메타데이터 관리

**현재 상태:** ❌ 미구현

---

#### 3. 동적 페르소나 추출 (`server/ai/pipelines/rag.py`의 `generate_persona_prompt`)
**목표:** 스크립트 데이터를 분석하여 강사의 말투 특징을 자동으로 추출하고 System Prompt에 주입

**구현 내용:**
- ✅ LLM을 사용한 말투 분석 (종결어미, 어투, 표현 패턴 등)
- ✅ 분석 결과를 System Prompt로 변환
- ✅ 페르소나 프롬프트를 벡터 DB에 저장

**현재 상태:** ✅ 부분 구현됨 (더 개선 가능)

---

#### 4. RAG 파이프라인 (`server/ai/pipelines/rag.py`)
**목표:** 지식 베이스 구축 및 검색 최적화

**구현 내용:**
- ✅ `ingest_texts()`: 텍스트 임베딩 및 벡터 DB 저장
- ✅ `query()`: course_id 필터링을 통한 하이브리드 검색
- ✅ LLM을 통한 답변 생성 (강의 컨텍스트 우선)
- ✅ 대화 히스토리 지원
- ⚠️ 검색 최적화 (하이브리드 검색 고도화 필요)

**현재 상태:** ✅ 기본 구현됨 (개선 가능)

---

#### 5. 파이프라인 오케스트레이션 (`server/ai/pipelines/processor.py` - 새로 생성 필요)
**목표:** STT → PDF 처리 → 페르소나 추출 → RAG 인제스트 전체 흐름 관리

**구현 내용:**
- ❌ `process_course_assets()` 함수 구현
- ❌ STT 처리 호출
- ❌ PDF 처리 호출 (멀티모달)
- ❌ 페르소나 추출 및 저장
- ❌ RAG 인제스트 (텍스트, 이미지 설명, 페르소나 모두)

**현재 상태:** ❌ `server/core/tasks.py`에 섞여있음 (백엔드 A 영역으로 이동 필요)

---

#### 6. 실시간 스트리밍 질의응답 (`server/ai/pipelines/rag.py`의 `query`)
**목표:** 1~2초 내 즉각 답변 생성

**구현 내용:**
- ✅ 빠른 답변 생성 (이미 구현됨)
- ❌ 스트리밍 출력 (SSE/WebSocket 지원 필요 - 백엔드 B와 협업)

**현재 상태:** ✅ 기본 구현됨, ⚠️ 스트리밍은 백엔드 B와 협업 필요

---

## 👤 백엔드 B (시스템 아키텍처 & 데이터 관리) - 이두호

**핵심 목표:** 대용량 파일 처리를 안정적으로 관리하고, 강사별 데이터를 엄격히 격리하는 플랫폼 환경 구축

### 📁 작업 공간
- `server/api/` 폴더 전체
- `server/core/` 폴더 전체 (단, AI 로직 제외)

### 🔧 구현해야 할 구체적 기능

#### 1. 비동기 Task 관리 (`server/core/tasks.py`)
**목표:** 영상 처리와 같은 고부하 작업을 위한 Background Task 관리

**구현 내용:**
- ✅ `enqueue_processing_task()` 함수: FastAPI Background Tasks 트리거
- ❌ 백엔드 A의 `processor.process_course_assets()` 호출 (아직 processor.py가 없음)
- ⚠️ 향후 Celery 등으로 확장 가능하도록 설계

**현재 상태:** ✅ 기본 구조 있음, ⚠️ 백엔드 A 함수 호출로 수정 필요

---

#### 2. 멀티 테넌트(Multi-tenant) DB 설계 (`server/core/models.py`)
**목표:** 강사(Instructor), 강의(Course), 학생(Student) 간의 관계와 권한을 관리하는 스키마 설계 및 데이터 격리

**구현 내용:**
- ✅ Instructor, Course, Video 모델 (이미 구현됨)
- ✅ course_id 기반 데이터 격리
- ⚠️ Student 모델 (추가 필요할 수 있음)
- ⚠️ 권한 관리 (인증/인가 시스템)
- ✅ ChatSession 모델 (이미 구현됨)

**현재 상태:** ✅ 기본 구조 있음

---

#### 3. API 엔드포인트 설계 (`server/api/routers.py`)
**목표:** 강사용 업로드 API, 학생용 채팅/영상 스트리밍 API 등 확장성 있는 RESTful API 구축

**구현 내용:**
- ✅ `POST /api/upload` - 강사용 업로드 API
- ✅ `GET /api/status/{course_id}` - 처리 상태 조회
- ✅ `POST /api/chat/ask` - 학생용 채팅 API
- ✅ `GET /api/video/{course_id}` - 영상 스트리밍
- ⚠️ 실시간 스트리밍 (SSE/WebSocket 엔드포인트 추가 필요)
- ⚠️ 타임라인 연동 API (백엔드 A와 협업)

**현재 상태:** ✅ 기본 API 구현됨, ⚠️ 스트리밍 및 타임라인 API 추가 필요

---

#### 4. 파일 스토리지 관리 (`server/core/storage.py`)
**목표:** 업로드된 파일의 안전한 저장 및 관리

**구현 내용:**
- ✅ `save_course_assets()` - 파일 저장
- ✅ instructor_id/course_id 기반 디렉토리 구조
- ⚠️ 향후 S3/GCS 연동 가능하도록 확장

**현재 상태:** ✅ 기본 구현됨

---

#### 5. 보안 및 가드레일 (`server/api/routers.py`, 새로 추가 필요)
**목표:** API 호출 제한 및 AI 답변의 윤리 가드레일 적용

**구현 내용:**
- ❌ API Rate Limiting
- ❌ 인증/인가 미들웨어
- ❌ AI 답변 필터링 (유해 콘텐츠 차단)
- ❌ 입력 검증 강화

**현재 상태:** ❌ 미구현

---

#### 6. DB 연결 및 초기화 (`server/core/db.py`)
**목표:** 데이터베이스 연결 관리 및 스키마 초기화

**구현 내용:**
- ✅ SQLModel/SQLAlchemy 엔진 설정
- ✅ `init_db()` 함수
- ✅ `get_session()` 함수
- ⚠️ 향후 PostgreSQL 연동 준비

**현재 상태:** ✅ 기본 구현됨

---

## ⚠️ 현재 문제점: 역할 혼재

### 문제 1: `server/core/tasks.py`에 백엔드 A 로직이 섞여있음
**현재 상태:**
- `process_course_assets()` 함수가 `server/core/tasks.py`에 있음
- 이 함수는 STT, PDF 처리, 페르소나 추출 등 백엔드 A의 핵심 로직을 포함

**해결 방안:**
- `process_course_assets()` 함수를 `server/ai/pipelines/processor.py`로 이동
- `server/core/tasks.py`는 `enqueue_processing_task()`만 남기고, 백엔드 A 함수 호출

---

### 문제 2: PDF 처리 로직이 아직 없음
**현재 상태:**
- `server/core/tasks.py`에 PDF 플레이스홀더만 있음
- PDF 처리 서비스가 구현되지 않음

**해결 방안:**
- 백엔드 A가 `server/ai/services/pdf.py`에 PDF 처리 로직 구현
- 텍스트 + 이미지 추출 및 Vision API 통합

---

## 📝 구현 우선순위 제안

### 백엔드 A (즉시 구현 필요)
1. ✅ STT 처리 (이미 완료)
2. ❌ **PDF 처리 서비스** (`server/ai/services/pdf.py`) - 기능 3
3. ❌ **파이프라인 오케스트레이션** (`server/ai/pipelines/processor.py`) - 기능 1, 2, 3 통합
4. ✅ RAG 파이프라인 (기본 완료, 개선 가능)
5. ✅ 페르소나 추출 (기본 완료, 개선 가능)

### 백엔드 B (즉시 구현 필요)
1. ✅ API 엔드포인트 (기본 완료)
2. ✅ DB 모델 (기본 완료)
3. ✅ 파일 스토리지 (기본 완료)
4. ⚠️ **Background Task 구조 정리** (`server/core/tasks.py`) - 백엔드 A 함수 호출로 수정
5. ❌ 보안 및 가드레일 (추가 필요)
6. ⚠️ 스트리밍 API (백엔드 A와 협업 필요)

