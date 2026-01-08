# 변경 이력 (Changelog)

이 문서는 프로젝트 개발 과정에서 이루어진 주요 변경사항을 정리한 것입니다.

---

## 📅 최근 변경사항

### 🎯 주요 기능 개선

#### 1. **요약노트 마크다운 렌더링 개선**
- **파일**: 
  - `server/api/routers.py` (요약 생성)
  - `client/components/SummaryNote.tsx` (렌더링)
  - `client/app/globals.css` (스타일링)
- **변경 내용**:
  - 서버에서 마크다운 → HTML 변환
  - 프론트엔드에서 `marked` 라이브러리로 fallback 처리
  - Notion 스타일의 시각적 마크다운 렌더링
  - 표, 불릿 포인트, 강조 텍스트 등 지원
  - LLM 응답에서 `<pre><code class="language-markdown">` 태그 자동 제거
  - "주요 포인트 요약" 섹션 제거
  - "중요 용어" 섹션 제거 (핵심 개념과 중복)
  - LLM 프롬프트 개선으로 중복 내용 방지

#### 2. **퀴즈 채점 로직 수정**
- **파일**: `server/api/routers.py`
- **변경 내용**:
  - 프론트엔드에서 전송된 퀴즈 문제 데이터를 사용하여 채점
  - 백엔드에서 퀴즈 재생성하지 않고 원본 문제로 채점
  - 정확한 점수 계산 보장

#### 3. **챗봇 시간 인식 기능**
- **파일**: 
  - `server/api/routers.py` (챗봇 엔드포인트)
  - `server/ai/pipelines/rag.py` (RAG 파이프라인)
  - `client/components/ChatPanel.tsx`
  - `client/components/VideoPlayer.tsx`
  - `client/app/student/play/[course_id]/page.tsx`
- **변경 내용**:
  - 현재 비디오 재생 시간을 챗봇에 전달
  - "지금 몇분대야" 같은 시간 관련 질문 직접 답변
  - "방금 뭐라고 했어?" 같은 질문에 현재 시간대 transcript 우선 사용
  - 현재 시간 ±30초 범위의 세그먼트를 컨텍스트로 활용
  - RAG 쿼리에 `current_time` 파라미터 추가

#### 4. **메인 화면 학생 중심 재구성**
- **파일**: `client/app/page.tsx`
- **변경 내용**:
  - 학생용 "강의 목록 보러가기" 버튼 강조
  - "강사 로그인" 버튼 추가
  - 학생 중심 UI/UX로 개선
  - 강사 ID 표시 제거

#### 5. **강사 로그인 시스템**
- **파일**: 
  - `client/app/instructor/login/page.tsx` (새로 생성)
  - `server/api/dh_routers.py` (로그인 엔드포인트)
- **변경 내용**:
  - 강사 ID 입력으로 로그인
  - 강사가 없으면 자동 생성
  - JWT 토큰 기반 인증
  - 로그인 후 강사 페이지로 이동
  - 로컬 스토리지에 토큰 저장

#### 6. **강사별 강의 목록 시스템**
- **파일**: 
  - `client/app/student/courses/page.tsx` (강사 선택)
  - `client/app/student/courses/[instructor_id]/page.tsx` (강사별 강의 목록)
- **변경 내용**:
  - 학생이 강사를 선택한 후 해당 강사의 강의만 표시
  - 강사별 강의 수 표시
  - 강의 상태별 시각적 구분
  - 강사 선택 후 바로 강의 목록 표시
  - 강사 ID 표시 제거 (학생 페이지)
  - 검색 및 카테고리 필터링 기능

#### 7. **강사 강의 관리 페이지**
- **파일**: 
  - `client/app/instructor/courses/page.tsx` (새로 생성)
  - `server/api/dh_routers.py` (강의 관리 API)
- **변경 내용**:
  - 강사가 자신의 강의 목록 조회
  - 강의 삭제 기능 (권한 체크 포함)
  - DB, 벡터 DB, 업로드 파일 모두 삭제
  - 강의 상태 표시 및 관리
  - 강의명/카테고리 인라인 편집 기능
  - 강사명 인라인 편집 기능
  - 강의 목록 생성 모달 추가
  - 미리보기 버튼 제거, 챕터 관리 버튼만 유지

#### 8. **SMI 자막 파일 지원**
- **파일**: 
  - `server/ai/services/smi_parser.py` (새로 생성)
  - `server/core/dh_tasks.py` (SMI 처리 로직)
  - `server/ai/pipelines/processor.py` (SMI 처리)
  - `client/components/UploadForm.tsx` (SMI 업로드 필드)
- **변경 내용**:
  - SMI (SAMI) 자막 파일 파싱
  - SMI 파일이 있으면 STT 건너뛰기
  - SMI → Transcript JSON 변환 (시간대 포함)
  - 여러 인코딩 지원 (UTF-8, CP949, EUC-KR, UTF-16)
  - HTML 태그 제거 및 텍스트 정리
  - 누락된 `</P>` 태그 처리

#### 9. **강사명/강의명 입력 기능**
- **파일**: 
  - `client/components/UploadForm.tsx` (입력 필드)
  - `server/api/dh_routers.py` (저장 로직)
  - `server/api/routers.py` (API 응답)
  - `client/app/student/courses/page.tsx` (표시)
  - `client/app/student/courses/[instructor_id]/page.tsx` (표시)
- **변경 내용**:
  - 업로드 시 강사명, 강의명 입력 가능
  - 강사명은 `Instructor.name`에 저장
  - 강의명은 `Course.title`에 저장
  - 학생 페이지에서 이름으로 표시 (있으면 이름, 없으면 ID)
  - 효율적인 강의 관리 가능
  - **챕터명/강의명 필수 입력으로 변경** (최신)

#### 10. **계층적 강의/챕터 구조**
- **파일**: 
  - `server/core/models.py` (데이터 모델)
  - `server/core/db.py` (데이터베이스 마이그레이션)
  - `server/api/dh_routers.py` (강의 생성/업로드 API)
  - `server/api/routers.py` (챕터 목록 조회 API)
  - `client/app/instructor/courses/page.tsx` (강의 목록 생성)
  - `client/app/instructor/courses/[course_id]/chapters/page.tsx` (챕터 관리)
  - `client/app/student/courses/[instructor_id]/[course_id]/chapters/page.tsx` (학생 챕터 보기)
  - `client/components/UploadForm.tsx` (챕터 업로드)
- **변경 내용**:
  - 부모 강의와 챕터 구조 지원
  - `parent_course_id`, `chapter_number`, `total_chapters` 필드 추가
  - 강의 목록 생성 기능 (파일 없이 부모 강의만 생성)
  - 챕터 업로드 시 자동 ID 생성 (`{parentCourseId}-{chapterNumber}`)
  - 챕터 번호 필수 입력
  - 챕터 목록 조회 API (`GET /api/courses/{course_id}/chapters`)
  - 강사 챕터 관리 페이지
  - 학생 챕터 보기 페이지
  - 챕터 목록 리스트 형식 UI (카드 → 테이블)
  - 챕터 행 전체 클릭 가능 (완료된 챕터만)

#### 11. **강의 플레이 페이지 UI 개선**
- **파일**: 
  - `client/app/student/play/[course_id]/page.tsx`
  - `server/api/routers.py` (강의 정보 조회 API)
- **변경 내용**:
  - 뒤로 가기 버튼 추가 (헤더 상단)
  - course ID 대신 강의명 표시
  - 강의 정보 조회 API 추가 (`GET /api/courses/{course_id}`)
  - "Course" → "강의 시청" 라벨 변경

#### 12. **채팅 패널 UI 개선**
- **파일**: 
  - `client/components/ChatPanel.tsx`
  - `client/app/student/play/[course_id]/page.tsx`
- **변경 내용**:
  - course ID 제거, "실시간 채팅"만 표시
  - 초기 메시지 개선 ("코스 {course_id} 채팅을 시작합니다" → "안녕하세요! 강의에 대해 궁금한 점이 있으시면 언제든지 질문해 주세요.")
  - 채팅 패널 높이 조정 (`h-[calc(100vh-15.5rem)]`)
  - 페이지 전체 스크롤 방지 (컨테이너 내부만 스크롤)
  - `scrollIntoView` → `scrollTo`로 변경하여 페이지 스크롤 방지

#### 13. **SummaryNote 및 Quiz 컴포넌트 개선**
- **파일**: 
  - `client/components/SummaryNote.tsx`
  - `client/components/Quiz.tsx`
- **변경 내용**:
  - course ID 제거, 강의명 표시
  - 강의 정보 조회 API 연동
  - 강의 정보를 가져오지 못할 경우 "로딩 중..." 표시

#### 14. **강의 검색 및 카테고리 필터링**
- **파일**: 
  - `server/api/routers.py`
  - `client/app/student/courses/page.tsx`
- **변경 내용**:
  - 강의명, 강사명으로 검색 기능
  - 카테고리별 필터링 기능
  - 검색어와 카테고리 동시 적용 가능

#### 15. **챗봇 UI 아이폰 메시지 스타일 적용**
- **파일**: `client/components/ChatPanel.tsx`
- **변경 내용**:
  - 아이폰 메시지 앱 스타일로 UI 개선
  - 사용자 메시지: 오른쪽 정렬, 파란색 배경
  - 봇 메시지: 왼쪽 정렬, 흰색 배경, 프로필 이미지 표시
  - 말풍선 모서리 둥글게 처리 (`rounded-2xl`)
  - 역할 표시 라벨 제거로 깔끔한 디자인

---

## 🔧 기술적 개선사항

### 백엔드
- **인증 시스템**: JWT 기반 강사/학생 인증
- **권한 관리**: 강사는 자신의 강의만 관리 가능
- **에러 처리**: 더 명확한 에러 메시지 및 처리
- **API 구조**: `/api/instructor/*` 엔드포인트 추가
- **데이터베이스 마이그레이션**: 
  - `category` 컬럼 추가
  - `parent_course_id`, `chapter_number`, `total_chapters` 컬럼 추가
  - 기존 테이블에 자동 마이그레이션 지원

### 프론트엔드
- **라우팅**: 학생/강사 경로 분리
- **상태 관리**: 로컬 스토리지로 로그인 상태 관리
- **UI/UX**: 학생 중심 디자인으로 개선
- **컴포넌트**: 재사용 가능한 컴포넌트 구조
- **Next.js 15 호환**: `params` Promise 처리 제거, `useParams` 훅 사용

---

## 📁 주요 파일 구조

### 새로 생성된 파일
- `client/app/instructor/login/page.tsx` - 강사 로그인 페이지
- `client/app/instructor/courses/page.tsx` - 강사 강의 관리 페이지
- `client/app/instructor/courses/[course_id]/chapters/page.tsx` - 강사 챕터 관리 페이지
- `client/app/student/courses/page.tsx` - 강사 선택 페이지
- `client/app/student/courses/[instructor_id]/page.tsx` - 강사별 강의 목록
- `client/app/student/courses/[instructor_id]/[course_id]/chapters/page.tsx` - 학생 챕터 보기 페이지
- `server/ai/services/smi_parser.py` - SMI 자막 파서

### 주요 수정 파일
- `server/api/routers.py` - 요약 생성, 퀴즈 채점, 챗봇 시간 인식, 강의 정보 조회, 챕터 목록 조회
- `server/api/dh_routers.py` - 강사 인증, 강의 관리 API, 강의 목록 생성, 강의/강사명 수정
- `server/api/dh_schemas.py` - `CreateCourseRequest`, `CourseUpdateRequest`, `InstructorProfileUpdateRequest` 스키마 추가
- `server/core/dh_tasks.py` - SMI 처리 로직 추가
- `server/core/db.py` - 데이터베이스 마이그레이션 함수 추가
- `server/core/models.py` - `parent_course_id`, `chapter_number`, `total_chapters`, `category` 필드 추가
- `server/core/config.py` - 데이터 폴더 경로 변경 (`server/data/`)
- `server/ai/config.py` - ChromaDB 경로 변경 (`server/data/chroma`)
- `server/ai/pipelines/processor.py` - SMI 처리 지원
- `server/ai/services/stt.py` - STT 속도 최적화
- `client/components/UploadForm.tsx` - 강사명/강의명 입력, SMI 업로드, 챕터 업로드 지원, 챕터명 필수 입력
- `client/components/SummaryNote.tsx` - 마크다운 렌더링 개선, 강의명 표시
- `client/components/Quiz.tsx` - 강의명 표시
- `client/components/ChatPanel.tsx` - 시간 인식 기능, course ID 제거, 스크롤 개선
- `client/components/VideoPlayer.tsx` - 시간 업데이트 콜백
- `client/app/page.tsx` - 학생 중심 메인 화면
- `client/app/student/play/[course_id]/page.tsx` - 뒤로 가기 버튼, 강의명 표시

---

## 🎨 UI/UX 개선

1. **학생 중심 디자인**: 메인 화면을 학생 관점으로 재구성
2. **강사 관리**: 강사가 자신의 강의를 효율적으로 관리
3. **이름 표시**: 강사명/강의명으로 더 직관적인 탐색
4. **시각적 피드백**: 강의 상태별 색상 및 아이콘 구분
5. **챕터 관리**: 리스트 형식으로 깔끔한 챕터 관리
6. **인라인 편집**: 강의명, 카테고리, 강사명 직접 수정
7. **Course ID 제거**: 사용자에게 기술적 ID 노출 최소화

---

## 🐛 버그 수정

1. **요약노트 마크다운 렌더링**: HTML 태그로 감싸진 마크다운 처리
2. **퀴즈 채점 오류**: 정확한 점수 계산 보장
3. **챗봇 시간 인식**: 현재 시간대 기반 답변 개선
4. **변수 스코프 오류**: `result` 변수 초기화 문제 해결
5. **이메일 검증 오류**: `EmailStr` → `Optional[str]`로 변경
6. **Next.js 15 params 오류**: `params.then is not a function` 해결 (`useParams` 훅 사용)
7. **페이지 스크롤 문제**: 채팅 패널 자동 스크롤이 페이지 전체를 스크롤하는 문제 해결
8. **Depends 함수 호출 오류**: `Depends(require_instructor)` → `Depends(require_instructor())` 수정

---

## 📝 API 변경사항

### 새로 추가된 엔드포인트
- `POST /api/auth/login` - 강사/학생 로그인
- `GET /api/instructor/courses` - 강사 강의 목록 조회
- `POST /api/instructor/courses` - 강의 목록 생성 (파일 없이)
- `PATCH /api/instructor/courses/{course_id}` - 강의 정보 수정 (제목, 카테고리)
- `PATCH /api/instructor/profile` - 강사 프로필 수정 (이름)
- `DELETE /api/instructor/courses/{course_id}` - 강사 강의 삭제
- `GET /api/courses/{course_id}` - 단일 강의 정보 조회
- `GET /api/courses/{course_id}/chapters` - 강의의 챕터 목록 조회

### 수정된 엔드포인트
- `POST /api/instructor/upload` - 강사명/강의명 파라미터 추가, SMI 파일 지원, 챕터 업로드 지원, `course_title` 필수
- `GET /api/courses` - 강사명 필드 추가, 검색어(`q`) 및 카테고리(`category`) 파라미터 추가, 메인 강의만 조회
- `POST /api/chat/ask` - `current_time` 파라미터 추가
- `POST /api/quiz/submit` - `questions` 파라미터 추가

---

## 🔐 보안 개선

1. **JWT 인증**: 강사/학생 인증 시스템
2. **권한 체크**: 강사는 자신의 강의만 관리 가능
3. **토큰 기반 API**: 인증이 필요한 엔드포인트에 토큰 검증
4. **의존성 주입 수정**: `Depends(require_instructor())` 올바른 호출

---

## 📚 사용 가이드

### 강사 사용법
1. 메인 화면 → "강사 로그인"
2. 강사 ID 입력 → 자동 로그인
3. 강사 페이지에서 강의 관리
4. "강의 목록 생성" 버튼으로 부모 강의 생성
5. 챕터 관리 페이지에서 챕터 추가
6. 업로드 시 강사명/강의명 필수 입력
7. 강의명/카테고리/강사명 인라인 편집 가능

### 학생 사용법
1. 메인 화면 → "강의 목록 보러가기"
2. 강사 선택
3. 강사별 강의 목록에서 강의 선택
4. 챕터가 있는 경우 챕터 목록에서 선택
5. 강의 시청 및 학습

---

## 🚀 향후 개선 가능 사항

1. 강의 통계 및 분석
2. 학생 학습 진도 추적
3. 강의 평가 및 리뷰
4. 다국어 지원
5. 모바일 반응형 디자인 개선

---

## 📊 데이터베이스 스키마 변경

### Course 테이블 추가 컬럼
- `title: Optional[str]` - 강의명
- `category: Optional[str]` - 강의 카테고리
- `parent_course_id: Optional[str]` - 부모 강의 ID (챕터인 경우)
- `chapter_number: Optional[int]` - 챕터 번호
- `total_chapters: Optional[int]` - 전체 강의 수 (부모 강의에만)

### Instructor 테이블 추가 컬럼
- `name: Optional[str]` - 강사명

### 마이그레이션
- 기존 테이블에 자동으로 컬럼 추가
- SQLite ALTER TABLE 문 사용
- 마이그레이션 실패 시에도 계속 진행 (이미 존재하는 경우)

---

## 📌 주요 결정 사항

1. **챕터명/강의명 필수 입력**: 모든 강의에 제목이 있어야 하므로 필수로 변경
2. **Course ID 노출 최소화**: 사용자에게는 강의명만 표시, 기술적 ID는 숨김
3. **계층적 구조**: 부모 강의와 챕터로 구조화하여 대규모 강의 관리 용이
