# 👥 옆강 프로젝트 협업 가이드

이 문서는 3명의 팀원이 각자의 역할에 맞춰 작업을 시작하기 위한 가이드입니다.

---

## 📁 프로젝트 구조 개요

```
Yeop-Gang/
├── server/                 # 백엔드 전체
│   ├── ai/                # 👤 백엔드 A 담당 영역
│   │   ├── pipelines/     # RAG 파이프라인
│   │   ├── services/      # STT, Vectorstore
│   │   └── config.py      # AI 설정
│   ├── api/               # 👤 백엔드 B 담당 영역
│   │   ├── routers.py     # API 엔드포인트
│   │   └── schemas.py     # 요청/응답 스키마
│   ├── core/              # 👤 백엔드 B 담당 영역
│   │   ├── models.py      # DB 모델 (Instructor, Course, Video, ChatSession)
│   │   ├── db.py          # DB 연결 및 초기화
│   │   ├── tasks.py       # Background Tasks (비동기 처리)
│   │   └── storage.py     # 파일 저장 관리
│   └── main.py            # FastAPI 앱 진입점
├── client/                # 👤 프론트엔드 담당 영역
│   ├── app/
│   │   ├── instructor/    # 강사용 페이지
│   │   └── student/       # 학생용 페이지
│   └── components/        # 재사용 컴포넌트
└── data/                  # 업로드 파일 및 DB 저장소
```

---

## 👤 백엔드 A (AI 엔진 & 자동화 파이프라인)

### 담당 영역
- `server/ai/` 폴더 전체
- Whisper STT 연동
- RAG 파이프라인 고도화
- 페르소나 추출 알고리즘
- 멀티모달 (PDF 이미지/도표) 처리

### 시작하기

#### 1. 환경 설정
```bash
cd server
source ../.venv/bin/activate  # 또는 python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

#### 2. 추가 설치 필요 패키지 (선택)
```bash
# OpenAI Whisper (로컬 실행 시)
pip install openai-whisper

# 또는 OpenAI API 사용 시 (현재 requirements.txt에 포함됨)
# openai 패키지로 Whisper API 호출 가능
```

#### 3. 환경 변수 설정
루트 `.env` 파일에 다음을 확인:
```
OPENAI_API_KEY=your-key-here
CHROMA_DB_PATH=./data/chroma
LLM_MODEL=gpt-4o-mini  # 또는 gpt-4o
EMBEDDING_MODEL=text-embedding-3-small
```

#### 4. 주요 작업 파일
- **STT 구현:** `server/ai/services/stt.py`
  - 현재 플레이스홀더 상태
  - OpenAI Whisper API 또는 로컬 Whisper 연동 필요
  - 타임스탬프 추출 로직 추가 필요

- **RAG 파이프라인:** `server/ai/pipelines/rag.py`
  - `query()` 메서드: LLM 응답 생성 로직 추가 필요
  - `ingest_texts()`: 임베딩 및 메타데이터 저장 로직 개선 필요
  - `generate_persona_prompt()`: 실제 스타일 분석 로직 구현 필요

- **Vectorstore:** `server/ai/services/vectorstore.py`
  - ChromaDB 컬렉션 관리

#### 5. 테스트 방법

**단위 테스트 (개별 함수 테스트):**
```bash
cd server
python -c "from ai.services.stt import transcribe_video; print(transcribe_video('test.mp4'))"
```

**통합 테스트 (API 엔드포인트 테스트):**
1. 서버 실행: `uvicorn main:app --reload --port 8000`
2. Swagger UI: http://localhost:8000/docs
3. `POST /ai/ingest` 엔드포인트로 텍스트/영상 업로드 테스트
4. `POST /ai/query` 엔드포인트로 RAG 검색 테스트

**전체 파이프라인 테스트:**
1. `POST /api/upload` 로 영상 업로드
2. `GET /api/status/{course_id}` 로 처리 상태 확인
3. `POST /api/chat/ask` 로 챗봇 질의 테스트

#### 6. 작업 우선순위 제안
1. ✅ **STT 연동** (`stt.py`) - Whisper API로 전사 + 타임스탬프 추출
2. ✅ **LLM 응답 생성** (`rag.py`의 `query()`) - GPT-4o로 RAG 응답 생성
3. ✅ **페르소나 분석** (`generate_persona_prompt()`) - 스타일 추출 로직 구현
4. ⏭️ **PDF 이미지 처리** - VLM 연동 (Phase 2)

---

## 👤 백엔드 B (시스템 아키텍처 & 데이터 관리)

### 담당 영역
- `server/api/` 폴더
- `server/core/` 폴더
- 비동기 Task 관리
- 멀티 테넌트 DB 설계 및 관리
- API 엔드포인트 설계
- 보안 및 가드레일

### 시작하기

#### 1. 환경 설정
```bash
cd server
source ../.venv/bin/activate
pip install -r requirements.txt
```

#### 2. 추가 설치 필요 패키지 (선택)
```bash
# Celery 사용 시 (현재는 FastAPI BackgroundTasks 사용 중)
pip install celery redis

# Rate limiting
pip install slowapi

# JWT 인증
pip install python-jose[cryptography] passlib[bcrypt]
```

#### 3. 환경 변수 설정
`.env` 파일에 다음 확인:
```
DATABASE_URL=sqlite:///./data/yeopgang.db
DATA_ROOT=./data
JWT_SECRET=your-secret-key
FRONTEND_URL=http://localhost:3000
BACKEND_URL=http://localhost:8000
```

#### 4. 주요 작업 파일
- **API 엔드포인트:** `server/api/routers.py`
  - `POST /api/upload` - 파일 업로드 (완료)
  - `GET /api/status/{course_id}` - 상태 조회 (완료)
  - `POST /api/chat/ask` - 챗봇 질의 (완료)
  - 추가 필요: 인증, Rate limiting, 에러 핸들링

- **DB 모델:** `server/core/models.py`
  - Instructor, Course, Video, ChatSession 모델 정의
  - 추가 필요: Student 모델, 권한 관리

- **Background Tasks:** `server/core/tasks.py`
  - `process_course_assets()` 함수가 백엔드 A의 파이프라인 호출
  - 추가 필요: 진행률 추적 (WebSocket 또는 Polling), 에러 핸들링

- **파일 스토리지:** `server/core/storage.py`
  - 업로드 파일 저장 로직
  - 추가 필요: S3/GCS 연동, 파일 정리 로직

#### 5. 테스트 방법

**DB 스키마 테스트:**
```bash
cd server
python -c "from core.db import init_db; init_db(); print('DB initialized')"
python -c "from core.models import Course, Instructor; print('Models OK')"
```

**API 엔드포인트 테스트:**
1. 서버 실행: `uvicorn main:app --reload --port 8000`
2. Swagger UI: http://localhost:8000/docs
3. 각 엔드포인트 순서대로 테스트:
   - `POST /api/upload` - 영상 업로드
   - `GET /api/status/{course_id}` - 상태 확인
   - `POST /api/chat/ask` - 채팅 테스트

**전체 플로우 테스트:**
```bash
# 업로드 테스트 (curl)
curl -X POST "http://localhost:8000/api/upload" \
  -F "instructor_id=test-1" \
  -F "course_id=test-course-1" \
  -F "video=@/path/to/video.mp4"

# 상태 확인
curl http://localhost:8000/api/status/test-course-1

# 채팅 테스트
curl -X POST "http://localhost:8000/api/chat/ask" \
  -H "Content-Type: application/json" \
  -d '{"course_id": "test-course-1", "question": "안녕하세요"}'
```

#### 6. 작업 우선순위 제안
1. ✅ **에러 핸들링** - 업로드 실패, 처리 실패 등 예외 처리
2. ✅ **인증/인가** - JWT 기반 강사/학생 인증
3. ✅ **Rate Limiting** - API 호출 제한
4. ✅ **진행률 추적** - WebSocket 또는 Polling으로 업로드 진행률 전송
5. ⏭️ **Celery 연동** - 대용량 파일 처리를 위한 작업 큐 (선택)

---

## 👤 프론트엔드 (플랫폼 UI/UX)

### 담당 영역
- `client/` 폴더 전체
- 강사 모드 UI
- 학생 모드 UI
- 타임라인 연동
- 동적 테마 시스템

### 시작하기

#### 1. 환경 설정
```bash
cd client
npm install
```

#### 2. 추가 설치 필요 패키지 (선택)
```bash
# 비디오 플레이어
npm install react-player

# HTTP 클라이언트
npm install axios

# WebSocket (실시간 상태 업데이트)
npm install socket.io-client

# 상태 관리 (선택)
npm install zustand  # 또는 redux
```

#### 3. 환경 변수 설정
`client/.env.local` 파일 생성 (선택사항):
```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

**참고:** 환경 변수를 설정하지 않으면 기본값 `http://localhost:8000`이 사용됩니다.
`.env.local.example` 파일을 참고하여 `.env.local` 파일을 생성할 수 있습니다.

#### 4. 주요 작업 파일
- **강사 업로드 페이지:** `client/app/instructor/upload/page.tsx`
  - ✅ 업로드 폼 API 연동 완료
  - ✅ 진행률 표시 컴포넌트 연결 완료
  - ✅ 에러 핸들링 및 재시도 기능 완료

- **학생 플레이 페이지:** `client/app/student/play/[course_id]/page.tsx`
  - ✅ 토글 방식 레이아웃 (강의 시청 / 요약노트 / 퀴즈)
  - ✅ 비디오 플레이어 + 채팅 패널 레이아웃 완료
  - ✅ API 연동 완료 (채팅, 비디오 URL)
  - ✅ 타임라인 클릭 시 비디오 이동 기능 완료

- **컴포넌트:**
  - `client/components/UploadForm.tsx` - ✅ 업로드 폼 API 연동 완료, 진행률 폴링, 에러 핸들링
  - `client/components/ChatPanel.tsx` - ✅ 채팅 패널 API 연동 완료, 타임스탬프 클릭, 자동 스크롤, 에러 핸들링
  - `client/components/VideoPlayer.tsx` - ✅ 비디오 플레이어 타임라인 연동 완료, 외부 제어 가능
  - `client/components/SummaryNote.tsx` - ✅ 강의 요약노트 생성, 핵심 요약 및 주요 포인트 표시
  - `client/components/Quiz.tsx` - ✅ 퀴즈 5문제 자동 생성, 객관식 답변 선택, 자동 채점 및 점수 표시
  - `client/components/ProgressBar.tsx` - ✅ 진행률 표시 (로딩 애니메이션 포함)
  - `client/components/StatusBadge.tsx` - ✅ 상태 표시 (완료)

#### 5. 테스트 방법

**로컬 개발 서버 실행:**
```bash
cd client
npm run dev
```

**브라우저 접속:**
- 강사 업로드: http://localhost:3000/instructor/upload
- 학생 플레이: http://localhost:3000/student/play/test-course-1

**API 연동 테스트:**
1. 백엔드 서버가 실행 중인지 확인 (`uvicorn main:app --reload --port 8000`)
2. 업로드 페이지에서 실제 파일 업로드 테스트
3. 네트워크 탭에서 API 호출 확인
4. 채팅에서 메시지 전송 테스트
5. 요약노트 탭에서 자동 요약 생성 확인
6. 퀴즈 탭에서 퀴즈 생성 및 채점 기능 확인

#### 6. 작업 우선순위 제안
1. ✅ **업로드 폼 API 연동** - `/api/upload` 호출 및 파일 업로드
2. ✅ **채팅 패널 API 연동** - `/api/chat/ask` 호출 및 메시지 표시
3. ✅ **상태 폴링** - 업로드 진행률 실시간 표시
4. ✅ **비디오 플레이어 연동** - 실제 비디오 URL 로드
5. ✅ **타임라인 클릭** - 답변 내 타임스탬프 클릭 시 비디오 이동
6. ✅ **요약노트 기능** - 강의 요약 자동 생성 및 표시
7. ✅ **퀴즈 기능** - 5문제 퀴즈 생성, 답변 선택, 자동 채점 및 점수 표시
8. ⏭️ **동적 테마** - 강사별 UI 커스터마이징 (Phase 2)

---

## 🤝 협업 포인트

### 1. 데이터 흐름 (업로드 → 처리 → 채팅)

```
[프론트엔드] POST /api/upload
    ↓
[백엔드 B] 파일 저장 + Background Task 트리거
    ↓
[백엔드 B] process_course_assets() 호출
    ↓
[백엔드 A] transcribe_video() → STT
    ↓
[백엔드 A] generate_persona_prompt() → 페르소나 추출
    ↓
[백엔드 A] pipeline.ingest_texts() → 벡터 DB 저장
    ↓
[백엔드 B] Course.status = "completed"
    ↓
[프론트엔드] 상태 폴링으로 완료 확인
    ↓
[프론트엔드] POST /api/chat/ask
    ↓
[백엔드 B] pipeline.query() 호출
    ↓
[백엔드 A] RAG 검색 + LLM 응답 생성
    ↓
[프론트엔드] 답변 표시 + 타임라인 이동
```

### 2. 인터페이스 계약

**백엔드 A가 제공해야 하는 인터페이스:**
- `transcribe_video(video_path: str) -> dict[str, Any]` - 타임스탬프 포함 전사 결과
- `generate_persona_prompt(course_id: str, sample_texts: list[str]) -> str` - 페르소나 프롬프트
- `pipeline.query(question: str, course_id: str) -> dict` - RAG 검색 + LLM 응답

**백엔드 B가 제공해야 하는 인터페이스:**
- `POST /api/upload` - 파일 업로드
- `GET /api/status/{course_id}` - 처리 상태 (진행률 포함)
- `POST /api/chat/ask` - 채팅 질의

**프론트엔드가 제공해야 하는 인터페이스:**
- 업로드 폼 UI
- 비디오 플레이어 + 채팅 패널 UI
- 타임라인 클릭 핸들러

### 3. Git 브랜치 전략 (권장)

```bash
# 메인 브랜치
main  # 프로덕션 배포용

# 개발 브랜치
develop  # 통합 개발 브랜치

# 기능 브랜치
feature/backend-a-stt        # 백엔드 A 작업
feature/backend-b-auth       # 백엔드 B 작업
feature/frontend-api-connect # 프론트엔드 작업
```

**작업 플로우:**
1. `develop` 브랜치에서 기능 브랜치 생성
2. 각자 작업 후 `develop`에 PR
3. 코드 리뷰 후 머지
4. 통합 테스트 후 `main`에 배포

---

## 🚨 주의사항

### 공통
- **`.env` 파일은 절대 커밋하지 마세요** (`.gitignore`에 포함됨)
- 환경 변수는 `.env.example` 참고
- `data/` 폴더도 커밋하지 마세요 (업로드 파일 및 DB)

### 백엔드 A
- `server/ai/` 폴더 내에서만 작업 (다른 폴더 수정 시 백엔드 B와 협의)
- API 스키마 변경 시 백엔드 B와 협의

### 백엔드 B
- `server/api/`, `server/core/` 폴더 작업
- DB 스키마 변경 시 마이그레이션 고려
- 백엔드 A의 인터페이스 변경 시 협의

### 프론트엔드
- `client/` 폴더 내에서만 작업
- API 엔드포인트 변경 시 백엔드 B와 협의
- 새로운 컴포넌트는 `components/` 폴더에 추가

---

## 📞 문의 및 이슈

작업 중 문제 발생 시:
1. 코드 주석에 `TODO` 또는 `FIXME` 표시
2. GitHub Issues에 상세 설명 작성
3. 팀원들과 논의 후 해결

---

## ✅ 체크리스트 (각자 작업 시작 전)

### 백엔드 A
- [ ] 가상환경 활성화 및 패키지 설치 완료
- [ ] `.env` 파일에 `OPENAI_API_KEY` 설정
- [ ] `python test_import.py` 실행 성공
- [ ] Swagger UI 접속 가능 (http://localhost:8000/docs)

### 백엔드 B
- [ ] 가상환경 활성화 및 패키지 설치 완료
- [ ] `.env` 파일 설정 완료
- [ ] `python test_import.py` 실행 성공
- [ ] Swagger UI 접속 가능
- [ ] `data/` 폴더 생성 확인

### 프론트엔드
- [ ] `npm install` 완료
- [ ] `npm run dev` 실행 성공
- [ ] http://localhost:3000 접속 가능
- [ ] 백엔드 서버가 실행 중인지 확인

---

**좋은 협업 되시길 바랍니다! 🚀**

