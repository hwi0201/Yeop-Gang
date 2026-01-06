# ChromaDB 데이터 초기화 가이드

## 문제 상황
- `test-course-audio-1`에 저장된 데이터가 "옷 입는 방법" 내용 (잘못된 데이터)
- 실제로는 "정승제 확률과 통계 수능 특강" 강의여야 함

## 해결 방법

### 방법 1: 벡터 DB 초기화 (권장)

```bash
# 벡터 DB 폴더 삭제
rm -rf data/chroma/

# 서버 재시작 (자동으로 새 컬렉션 생성됨)
# 올바른 강의 파일로 재업로드
```

### 방법 2: 새로운 course_id로 업로드

올바른 강의 파일로 새로운 course_id 사용:

```bash
# 새로운 course_id로 업로드
curl -X POST "http://localhost:8000/api/upload" \
  -F "instructor_id=prob-stat-instructor" \
  -F "course_id=prob-stat-course-1" \
  -F "video=@ref/audio/[올바른_오디오_파일].mp3"
```

### 방법 3: 특정 course_id 데이터만 삭제 (고급)

현재는 전체 초기화만 가능합니다. 
필요하면 Python 스크립트로 특정 course_id의 문서만 삭제할 수 있습니다.

## 다음 단계

1. `ref/audio/testaudio_1.mp3` 파일 확인
   - 올바른 "정승제 확률과 통계" 강의 파일인지 확인
   - 잘못된 파일이면 올바른 파일로 교체

2. 벡터 DB 초기화 후 재업로드

3. 새로운 course_id 사용 권장

