# TEST_SEQUENCE.md 설명

## 📝 41-58 라인 내용 요약

이 부분은 **"테스트를 위해 파일을 업로드하는 방법"**을 설명하고 있습니다.

---

## 🤔 왜 업로드가 필요한가?

### 문제 상황

- 서버를 실행해도 자동으로 비디오를 처리하지 **않습니다**
- 챗봇이 답변하려면 먼저 비디오/오디오를 분석해야 합니다
- 분석하려면 **파일을 업로드**해야 합니다

### 해결 방법

- `/api/upload` 엔드포인트로 파일을 업로드하면
- 백그라운드에서 자동으로 STT (음성→텍스트) 처리가 시작됩니다

---

## 📋 명령어 설명

### 명령어 1: 오디오 파일 업로드

```bash
curl -X POST "http://localhost:8000/api/upload" \
  -F "instructor_id=test-instructor-1" \
  -F "course_id=test-course-1" \
  -F "video=@ref/audio/testaudio_1.mp3"
```

**의미:**

- `curl`: HTTP 요청을 보내는 명령어
- `-X POST`: POST 요청 (데이터 전송)
- `http://localhost:8000/api/upload`: 업로드 API 주소
- `-F`: Form 데이터 (파일 업로드 시 사용)
- `instructor_id=test-instructor-1`: 강사 ID
- `course_id=test-course-1`: 강의 ID (나중에 이 ID로 조회)
- `video=@ref/audio/testaudio_1.mp3`: 업로드할 파일 경로

**실제로 하는 일:**

1. `ref/audio/testaudio_1.mp3` 파일을 서버로 전송
2. 서버가 파일을 저장하고 처리 시작
3. STT → 임베딩 → 페르소나 생성 (백그라운드)

### 명령어 2: 비디오 파일 업로드

```bash
curl -X POST "http://localhost:8000/api/upload" \
  -F "instructor_id=test-instructor-1" \
  -F "course_id=test-course-1" \
  -F "video=@ref/video/testvedio_1.mp4"
```

**의미:**

- 오디오 대신 비디오 파일 업로드
- 나머지는 동일

---

## 🎯 실제 사용 시나리오

### 시나리오 1: 프론트엔드에서 업로드 (추천)

**이미 구현되어 있습니다!**

1. 브라우저에서 `http://localhost:3000/instructor/upload` 접속
2. Instructor ID, Course ID 입력
3. 비디오 파일 선택
4. "업로드" 버튼 클릭
5. **끝!** (명령어 입력 불필요)

### 시나리오 2: 명령어로 업로드 (테스트용)

**프론트엔드가 없거나 빠른 테스트가 필요할 때:**

```bash
# PowerShell에서 (Windows)
curl.exe -X POST "http://localhost:8000/api/upload" `
  -F "instructor_id=test-1" `
  -F "course_id=test-1" `
  -F "video=@ref/video/testvedio_1.mp4"

# 또는 실제 파일 경로 사용
curl.exe -X POST "http://localhost:8000/api/upload" `
  -F "instructor_id=test-1" `
  -F "course_id=test-1" `
  -F "video=@C:\Users\...\KakaoTalk_20260104_174104213.mp4"
```

---

## ⚠️ 주의사항

### 1. 서버가 실행 중이어야 함

```bash
# 터미널에서 서버 실행
cd server
uvicorn main:app --reload
```

### 2. 파일 경로 확인

- `ref/audio/testaudio_1.mp3`: 프로젝트 루트 기준 상대 경로
- 실제 파일이 있는지 확인 필요

### 3. 업로드 후 처리 시간

- 업로드는 즉시 완료
- **처리(STT 등)는 백그라운드에서 1-5분 소요**
- 상태 확인: `curl http://localhost:8000/api/status/test-course-1`

---

## 🔄 전체 흐름

```
1. 서버 실행
   ↓
2. 파일 업로드 (/api/upload)
   ↓
3. 서버가 파일 저장 (data/uploads/{instructor_id}/{course_id}/)
   ↓
4. 백그라운드 작업 시작 (STT 처리)
   ↓
5. 상태 확인 (/api/status/{course_id})
   - processing → completed 대기
   ↓
6. 처리 완료 후 챗봇 사용 가능
```

---

## 💡 간단 요약

**질문: 이 명령어는 뭐하는 거야?**

**답변:**

- 테스트용 비디오/오디오 파일을 서버에 업로드하는 명령어입니다
- 업로드하면 자동으로 STT 처리 등이 시작됩니다
- 하지만 **프론트엔드에서 업로드 버튼을 누르는 게 더 쉬워요!**

**언제 사용하나요?**

- 프론트엔드가 없을 때
- 빠른 테스트가 필요할 때
- 자동화 스크립트를 만들 때

**안 써도 되나요?**

- 네! 프론트엔드에서 업로드하면 명령어 없이도 됩니다!
