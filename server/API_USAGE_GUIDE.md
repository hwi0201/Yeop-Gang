# 백엔드 B 구현 요약 및 API 사용 가이드

## 📋 구현 완료된 기능 요약

### 1. 멀티 테넌트 DB 모델 확장 (`server/core/dh_models.py`)

- ✅ **Student 모델**: 학생 정보 관리
- ✅ **CourseEnrollment 모델**: 학생-강의 등록 관계 관리
- ✅ 데이터 격리: 강사는 자신의 강의만, 학생은 등록한 강의만 접근 가능

### 2. 비동기 Task 관리 개선 (`server/core/dh_tasks.py`)

- ✅ 백엔드 A의 `processor.process_course_assets()` 호출 구조
- ✅ 백엔드 A processor가 없을 경우 폴백 처리
- ✅ 에러 핸들링 및 로깅

### 3. 인증/인가 시스템 (`server/core/dh_auth.py`)

- ✅ JWT 기반 인증
- ✅ 역할 기반 접근 제어 (RBAC)
- ✅ 강사/학생 권한 분리
- ✅ 강의 접근 권한 검증 (멀티 테넌트 데이터 격리)

### 4. Rate Limiting (`server/core/dh_rate_limit.py`)

- ✅ API 호출 제한 미들웨어
- ✅ IP 및 사용자별 제한 (시간당 100회 기본값)
- ✅ Rate limit 헤더 제공

### 5. AI 답변 가드레일 (`server/core/dh_guardrails.py`)

- ✅ 윤리 가이드라인 적용
- ✅ 부적절한 콘텐츠 필터링
- ✅ 답변 품질 검증

### 6. API 엔드포인트 개선 (`server/api/dh_routers.py`)

- ✅ 강사 전용 엔드포인트
- ✅ 학생 전용 엔드포인트
- ✅ 공통 엔드포인트 (권한 체크 포함)
- ✅ 가드레일 적용된 채팅 API

---

## 🔐 인증 시스템 사용법

### 1. 강사 등록

```bash
POST /api/auth/register/instructor
Content-Type: application/json

{
  "id": "instructor-1",
  "name": "홍길동",
  "email": "instructor@example.com",
  "password": "password123"
}
```

**응답:**

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "user_id": "instructor-1",
  "role": "instructor",
  "expires_in": 86400
}
```

### 2. 학생 등록

```bash
POST /api/auth/register/student
Content-Type: application/json

{
  "id": "student-1",
  "name": "김철수",
  "email": "student@example.com",
  "password": "password123"
}
```

### 3. 로그인

```bash
POST /api/auth/login
Content-Type: application/json

{
  "user_id": "instructor-1",
  "password": "password123",
  "role": "instructor"
}
```

**응답:**

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "user_id": "instructor-1",
  "role": "instructor",
  "expires_in": 86400
}
```

### 4. 인증 헤더 사용

모든 보호된 엔드포인트는 다음 헤더가 필요합니다:

```
Authorization: Bearer <access_token>
```

---

## 👨‍🏫 강사 전용 API

### 1. 강의 업로드

```bash
POST /api/instructor/upload
Authorization: Bearer <instructor_token>
Content-Type: multipart/form-data

instructor_id: instructor-1
course_id: course-1
video: <file> (선택)
pdf: <file> (선택)
```

**응답:**

```json
{
  "course_id": "course-1",
  "instructor_id": "instructor-1",
  "status": "processing"
}
```

**주의사항:**

- 자신의 `instructor_id`와 일치해야 함
- 다른 강사의 강의는 업로드 불가

### 2. 강의 목록 조회

```bash
GET /api/instructor/courses
Authorization: Bearer <instructor_token>
```

**응답:**

```json
[
  {
    "id": "course-1",
    "title": "Python 기초",
    "status": "completed",
    "created_at": "2024-01-01T00:00:00"
  }
]
```

---

## 👨‍🎓 학생 전용 API

### 1. 강의 등록

```bash
POST /api/student/enroll
Authorization: Bearer <student_token>
Content-Type: application/json

{
  "course_id": "course-1"
}
```

**응답:**

```json
{
  "enrollment_id": 1,
  "student_id": "student-1",
  "course_id": "course-1",
  "status": "active",
  "enrolled_at": "2024-01-01T00:00:00"
}
```

### 2. 등록한 강의 목록 조회

```bash
GET /api/student/courses
Authorization: Bearer <student_token>
```

**응답:**

```json
[
  {
    "id": "course-1",
    "title": "Python 기초",
    "status": "completed",
    "enrolled_at": "2024-01-01T00:00:00"
  }
]
```

---

## 🔄 공통 API (강사/학생 모두 사용 가능)

### 1. 처리 상태 조회

```bash
GET /api/status/{course_id}
Authorization: Bearer <token>
```

**응답:**

```json
{
  "course_id": "course-1",
  "status": "completed",
  "progress": 100,
  "message": null,
  "stage": "completed",
  "error": null
}
```

**권한:**

- 강사: 자신의 강의만 조회 가능
- 학생: 등록한 강의만 조회 가능

### 2. 비디오 스트리밍

```bash
GET /api/video/{course_id}
Authorization: Bearer <token>
```

**응답:** 비디오 파일 스트리밍

**권한:**

- 강사: 자신의 강의만 접근 가능
- 학생: 등록한 강의만 접근 가능

### 3. 챗봇 질의 (가드레일 적용)

```bash
POST /api/chat/ask
Authorization: Bearer <token>
Content-Type: application/json

{
  "course_id": "course-1",
  "question": "Python에서 리스트는 어떻게 사용하나요?",
  "conversation_id": "optional-conversation-id"
}
```

**응답:**

```json
{
  "answer": "Python에서 리스트는 다음과 같이 사용합니다...",
  "sources": ["document-1", "document-2"],
  "conversation_id": "student-1:course-1",
  "course_id": "course-1",
  "is_safe": true,
  "filtered": false
}
```

**특징:**

- 가드레일 자동 적용 (부적절한 콘텐츠 필터링)
- 대화 히스토리 지원
- 권한 체크 (등록한 강의만 질의 가능)

---

## 🛡️ 보안 기능

### Rate Limiting

모든 API 요청은 Rate Limiting이 적용됩니다:

- 기본값: 시간당 100회 요청
- 헤더로 제한 정보 확인 가능:
  - `X-RateLimit-Limit`: 최대 요청 수
  - `X-RateLimit-Remaining`: 남은 요청 수
  - `X-RateLimit-Reset`: 리셋 시간

**Rate Limit 초과 시:**

```json
{
  "detail": "Rate limit exceeded. Try again in 3600 seconds."
}
```

HTTP Status: `429 Too Many Requests`

### 가드레일

채팅 API의 모든 답변은 가드레일이 적용됩니다:

- 금지 키워드 필터링
- 답변 품질 검증
- 안전하지 않은 답변은 기본 메시지로 대체

---

## 📝 사용 예시 (cURL)

### 1. 강사 등록 및 강의 업로드

```bash
# 1. 강사 등록
curl -X POST http://localhost:8000/api/auth/register/instructor \
  -H "Content-Type: application/json" \
  -d '{
    "id": "instructor-1",
    "name": "홍길동",
    "email": "instructor@example.com",
    "password": "password123"
  }'

# 2. 로그인
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "instructor-1",
    "password": "password123",
    "role": "instructor"
  }'
# 응답에서 access_token 저장

# 3. 강의 업로드
curl -X POST http://localhost:8000/api/instructor/upload \
  -H "Authorization: Bearer <access_token>" \
  -F "instructor_id=instructor-1" \
  -F "course_id=course-1" \
  -F "video=@video.mp4"
```

### 2. 학생 등록 및 강의 수강

```bash
# 1. 학생 등록
curl -X POST http://localhost:8000/api/auth/register/student \
  -H "Content-Type: application/json" \
  -d '{
    "id": "student-1",
    "name": "김철수",
    "email": "student@example.com",
    "password": "password123"
  }'

# 2. 로그인
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "student-1",
    "password": "password123",
    "role": "student"
  }'
# 응답에서 access_token 저장

# 3. 강의 등록
curl -X POST http://localhost:8000/api/student/enroll \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "course_id": "course-1"
  }'

# 4. 챗봇 질의
curl -X POST http://localhost:8000/api/chat/ask \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "course_id": "course-1",
    "question": "Python에서 리스트는 어떻게 사용하나요?"
  }'
```

---

## 🔧 환경 변수 설정

`.env` 파일에 다음 변수 설정:

```env
# JWT 인증
JWT_SECRET=your-secret-key-change-in-production

# 데이터베이스
DATABASE_URL=sqlite:///./data/yeopgang.db
DATA_ROOT=./data

# Rate Limiting (선택)
RATE_LIMIT_MAX_REQUESTS=100
RATE_LIMIT_WINDOW_SECONDS=3600
```

---

## 📌 주요 특징

1. **멀티 테넌트 데이터 격리**: 강사는 자신의 강의만, 학생은 등록한 강의만 접근
2. **JWT 기반 인증**: 안전한 토큰 기반 인증
3. **Rate Limiting**: API 남용 방지
4. **가드레일**: AI 답변의 윤리적 검증
5. **역할 기반 접근 제어**: 강사/학생 권한 분리

---

## ⚠️ 주의사항

1. **기존 API 호환성**: 기존 `/api/upload`, `/api/chat/ask` 등은 여전히 작동하지만, 보안 기능이 없습니다.
2. **새로운 API 사용 권장**: 보안 기능이 포함된 `/api/instructor/*`, `/api/student/*` 엔드포인트 사용을 권장합니다.
3. **백엔드 A processor**: 백엔드 A의 `processor.py`가 구현되면 자동으로 사용됩니다.

---

## 🔄 마이그레이션 가이드

기존 코드를 새로운 보안 API로 마이그레이션:

1. **인증 추가**: 모든 요청에 `Authorization: Bearer <token>` 헤더 추가
2. **엔드포인트 변경**:
   - `/api/upload` → `/api/instructor/upload` (강사만)
   - `/api/chat/ask` → `/api/chat/ask` (권한 체크 추가)
3. **에러 처리**: 401, 403, 429 에러 처리 추가

---

## 📚 실제 사용 예시 코드

더 자세한 예시는 `server/examples/` 폴더를 참고하세요:

- **`api_examples.py`**: Python 코드 예시 (완전한 워크플로우)
- **`curl_examples.sh`**: cURL 명령어 예시

### 빠른 시작 (Python)

```python
from examples.api_examples import YeopGangAPI

# API 클라이언트 생성
api = YeopGangAPI()

# 강사 등록 및 로그인
api.register_instructor("instructor-1", "홍길동", "hong@example.com", "pass123")

# 강의 업로드
api.upload_course("instructor-1", "course-1", video_path="video.mp4")

# 학생 등록 및 강의 수강
api.register_student("student-1", "김철수", "kim@example.com", "pass123")
api.enroll_course("course-1")

# 챗봇 질의
result = api.ask_chat("course-1", "Python 리스트 사용법은?")
print(result["answer"])
```
