# 옆강 프로젝트 작동 검사 가이드

## 📋 현재 구현 상태 요약

### ✅ 완료된 부분

#### **Backend A (AI Engine) - `/server/ai`**
- ✅ RAG 파이프라인 기본 구조 (`pipelines/rag.py`)
  - `course_id` 기반 메타데이터 필터링 지원
  - ChromaDB 벡터스토어 연동
  - 페르소나 프롬프트 생성 스텁 (`generate_persona_prompt`)
- ✅ Vectorstore 서비스 (`services/vectorstore.py`)
  - course별 컬렉션 분리 지원
- ⚠️ STT 서비스 (`services/stt.py`) - **플레이스홀더만 구현됨**
  - 실제 Whisper 연동 필요

#### **Backend B (API/Infra) - `/server/api`**
- ✅ DB 스키마 완료 (`core/models.py`)
  - Instructor, Course, Video, ChatSession 모델
  - 상태 관리 (processing/completed/failed)
- ✅ API 엔드포인트 구현 (`api/routers.py`)
  - `POST /api/upload` - 파일 업로드 및 백그라운드 처리 트리거
  - `GET /api/status/{course_id}` - 처리 상태 조회
  - `POST /api/chat/ask` - course_id 기반 챗봇 질의
  - `GET /api/health` - 헬스체크
- ✅ 파일 스토리지 관리 (`core/storage.py`)
- ✅ 백그라운드 태스크 파이프라인 (`core/tasks.py`)
  - STT → 임베딩 → 페르소나 생성 흐름

#### **Frontend - `/client`**
- ✅ 업로드 페이지 (`/instructor/upload`)
  - 파일 업로드 폼 컴포넌트
  - 상태 표시 배지
- ✅ 학생용 플레이 페이지 (`/student/play/[course_id]`)
  - 비디오 플레이어 + 채팅 패널 통합
- ✅ 기본 레이아웃 및 스타일링 (Tailwind CSS)

### ⚠️ TODO / 미완성 부분

1. **STT 실제 구현** (`server/ai/services/stt.py`)
   - OpenAI Whisper API 또는 로컬 Whisper 모델 연동 필요
2. **LLM 응답 생성** (`server/ai/pipelines/rag.py`)
   - 현재는 플레이스홀더만 반환, 실제 GPT-4o/Gemini 연동 필요
3. **페르소나 분석 로직**
   - 말투 추출 알고리즘 구현 필요
4. **프론트엔드 API 연동**
   - 실제 백엔드 엔드포인트 호출 연결 필요

---

## 🧪 작동 검사 방법

### 1. 환경 준비

```bash
# 프로젝트 루트로 이동
cd /Users/mac/Desktop/hateslop/Yeop-Gang

# Python 가상환경 활성화 (Python 3.11 권장)
source .venv/bin/activate  # 또는 python3.11 -m venv .venv && source .venv/bin/activate

# 의존성 설치
cd server
pip install -r requirements.txt

# 프론트엔드 의존성 설치
cd ../client
npm install
```

### 2. 환경 변수 설정

루트 디렉토리 `.env` 파일 확인:
```bash
# .env 파일이 루트에 있는지 확인
cat .env
```

필수 변수:
- `OPENAI_API_KEY` (STT 및 LLM용)
- `CHROMA_DB_PATH=./data/chroma`
- `DATABASE_URL=sqlite:///./data/yeopgang.db` (또는 PostgreSQL)

### 3. 백엔드 서버 실행

```bash
cd server
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

서버가 정상 실행되면:
- http://localhost:8000/ - 루트 엔드포인트 (API 정보)
- http://localhost:8000/docs - Swagger UI
- http://localhost:8000/api/health - 헬스체크

### 4. 프론트엔드 실행

```bash
cd client
npm run dev
```

- http://localhost:3000 접속

### 5. 단계별 테스트

#### **Step 1: 헬스체크**
```bash
curl http://localhost:8000/api/health
```
예상 응답: `{"status":"ok","service":"Yeop-Gang"}`

#### **Step 2: 강사 업로드 테스트**

**방법 A: Swagger UI 사용**
1. http://localhost:8000/docs 접속
2. `POST /api/upload` 엔드포인트 클릭
3. "Try it out" 클릭
4. `instructor_id`, `course_id` 입력
5. 파일 업로드 (다운받은 강의 영상)
6. Execute

**방법 B: curl 사용**
```bash
curl -X POST "http://localhost:8000/api/upload" \
  -H "Content-Type: multipart/form-data" \
  -F "instructor_id=test-instructor-1" \
  -F "course_id=test-course-1" \
  -F "video=@/path/to/your/video.mp4"
```

**방법 C: 프론트엔드 UI 사용**
1. http://localhost:3000/instructor/upload 접속
2. 강사 ID, 코스 ID 입력
3. 비디오 파일 선택 후 업로드

#### **Step 3: 처리 상태 확인**
```bash
curl http://localhost:8000/api/status/test-course-1
```
예상 응답: `{"course_id":"test-course-1","status":"processing","progress":0}`

**주의**: STT가 플레이스홀더이므로 실제 처리는 완료되지 않을 수 있습니다.

#### **Step 4: 채팅 테스트 (처리 완료 후)**
```bash
curl -X POST "http://localhost:8000/api/chat/ask" \
  -H "Content-Type: application/json" \
  -d '{
    "course_id": "test-course-1",
    "question": "이 강의의 핵심 내용은 무엇인가요?",
    "session_id": "test-session-1"
  }'
```

또는 프론트엔드에서:
1. http://localhost:3000/student/play/test-course-1 접속
2. 채팅창에 질문 입력

---

## 🔍 문제 해결

### 문제 1: `tiktoken` 빌드 실패
**해결**: Python 3.11 사용 또는 Rust 설치
```bash
# Python 3.11로 가상환경 재생성
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 문제 2: DB 초기화 오류 (SQLite 경로 문제)
**해결**: 코드에서 자동으로 프로젝트 루트 `data/` 폴더로 폴백 처리됨
- `server/core/db.py`의 `_prepare_sqlite_url()` 함수가 권한 문제 시 자동으로 프로젝트 내부 경로로 변경
- 수동으로 생성하려면: `mkdir -p data`

### 문제 3: 프론트엔드 CORS 오류
**해결**: `server/main.py`의 CORS 설정 확인 (현재 `allow_origins=["*"]`로 설정됨)

### 문제 4: Pydantic 설정 오류 (DotenvType 관련)
**해결**: 이미 해결됨. `pydantic-settings` 대신 `dataclass` + `os.getenv` 사용
- `server/ai/config.py`, `server/core/config.py` 모두 `@dataclass` 사용
- `.env` 파일 로딩은 `server/main.py`에서 `load_dotenv()` 사용 (권한 오류 시 자동 무시)

### 문제 5: Import 오류 (모듈을 찾을 수 없음)
**해결**: `python test_import.py` 실행하여 확인
```bash
cd server
source ../.venv/bin/activate
python test_import.py
# ✅ Main app imported successfully! 메시지가 나오면 정상
```

### 문제 6: STT가 작동하지 않음
**현재 상태**: 플레이스홀더만 구현됨. 실제 Whisper 연동 필요.
- OpenAI Whisper API 사용 시: `server/ai/services/stt.py` 수정 필요
- 로컬 Whisper 사용 시: `openai-whisper` 패키지 설치 필요

---

## 📝 다음 단계 (팀원별 작업)

### Backend A (AI Engine)
1. `server/ai/services/stt.py` - Whisper 실제 연동
2. `server/ai/pipelines/rag.py` - LLM 응답 생성 로직 구현
3. 페르소나 분석 알고리즘 고도화

### Backend B (API/Infra)
1. PostgreSQL 연동 (현재는 SQLite)
2. 인증/인가 시스템 추가
3. WebSocket으로 실시간 상태 업데이트

### Frontend
1. API 호출 실제 연결
2. 에러 핸들링 및 로딩 상태
3. 비디오 플레이어 타임라인 연동

---

## ✅ 검사 체크리스트

- [ ] 백엔드 서버가 정상 실행됨 (`/api/health` 응답 확인)
- [ ] 프론트엔드가 정상 실행됨 (http://localhost:3000 접속 가능)
- [ ] 업로드 API가 파일을 받음 (Swagger 또는 curl 테스트)
- [ ] 상태 조회 API가 응답함
- [ ] DB에 Course/Video 레코드가 생성됨 (`data/yeopgang.db` 확인)
- [ ] 프론트엔드 업로드 페이지가 렌더링됨
- [ ] 프론트엔드 플레이 페이지가 렌더링됨

**주의**: STT와 LLM 연동이 완료되지 않아 실제 AI 기능은 아직 작동하지 않습니다.

