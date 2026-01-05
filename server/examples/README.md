# API 사용 예시

이 폴더에는 백엔드 B API를 사용하는 다양한 예시가 포함되어 있습니다.

## 파일 목록

1. **`api_examples.py`** - Python 코드 예시
2. **`curl_examples.sh`** - cURL 명령어 예시

## 실행 방법

### Python 예시 실행

```bash
# 서버 실행 (별도 터미널)
uvicorn main:app --reload

# 예시 실행
cd server/examples
python api_examples.py
```

### cURL 예시 실행

```bash
# 서버 실행 (별도 터미널)
uvicorn main:app --reload

# 예시 실행 (Linux/Mac)
chmod +x curl_examples.sh
./curl_examples.sh

# Windows PowerShell
# curl_examples.sh의 내용을 PowerShell 스크립트로 변환하여 실행
```

## 예시 시나리오

### 시나리오 1: 강사 워크플로우

1. 강사 등록
2. 강의 업로드
3. 강의 목록 조회
4. 처리 상태 확인

### 시나리오 2: 학생 워크플로우

1. 학생 등록
2. 강의 등록
3. 등록한 강의 목록 조회
4. 챗봇 질의
5. 대화 히스토리 포함 질의

### 시나리오 3: 에러 처리

1. 인증 없이 접근 시도
2. 잘못된 토큰으로 접근 시도
3. 권한 없는 리소스 접근 시도

## 필수 패키지

Python 예시를 실행하려면:

```bash
pip install requests
```

## 주의사항

1. 서버가 실행 중이어야 합니다 (`uvicorn main:app --reload`)
2. 실제 파일 경로를 사용하는 경우 파일이 존재하는지 확인하세요
3. 데이터베이스가 초기화되어 있어야 합니다
