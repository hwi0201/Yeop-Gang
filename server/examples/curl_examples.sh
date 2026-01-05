#!/bin/bash
# 백엔드 B API 사용 예시 (cURL)
# 서버가 실행 중이어야 합니다: uvicorn main:app --reload

BASE_URL="http://localhost:8000/api"

echo "=========================================="
echo "옆강 API 사용 예시 (cURL)"
echo "=========================================="

# ==================== 예시 1: 강사 워크플로우 ====================
echo ""
echo "예시 1: 강사 워크플로우"
echo "----------------------------------------"

# 1. 강사 등록
echo "1. 강사 등록 중..."
INSTRUCTOR_REGISTER=$(curl -s -X POST "$BASE_URL/auth/register/instructor" \
  -H "Content-Type: application/json" \
  -d '{
    "id": "instructor-1",
    "name": "홍길동",
    "email": "hong@example.com",
    "password": "password123"
  }')

echo "응답: $INSTRUCTOR_REGISTER"
INSTRUCTOR_TOKEN=$(echo $INSTRUCTOR_REGISTER | jq -r '.access_token')
echo "토큰: ${INSTRUCTOR_TOKEN:0:50}..."
echo ""

# 2. 강의 업로드
echo "2. 강의 업로드 중..."
UPLOAD_RESULT=$(curl -s -X POST "$BASE_URL/instructor/upload" \
  -H "Authorization: Bearer $INSTRUCTOR_TOKEN" \
  -F "instructor_id=instructor-1" \
  -F "course_id=course-1" \
  -F "video=@ref/video/testvedio_1.mp4")

echo "응답: $UPLOAD_RESULT"
echo ""

# 3. 강의 목록 조회
echo "3. 강의 목록 조회 중..."
COURSES=$(curl -s -X GET "$BASE_URL/instructor/courses" \
  -H "Authorization: Bearer $INSTRUCTOR_TOKEN")

echo "강의 목록: $COURSES"
echo ""

# 4. 처리 상태 확인
echo "4. 처리 상태 확인 중..."
STATUS=$(curl -s -X GET "$BASE_URL/status/course-1" \
  -H "Authorization: Bearer $INSTRUCTOR_TOKEN")

echo "상태: $STATUS"
echo ""

# ==================== 예시 2: 학생 워크플로우 ====================
echo ""
echo "예시 2: 학생 워크플로우"
echo "----------------------------------------"

# 1. 학생 등록
echo "1. 학생 등록 중..."
STUDENT_REGISTER=$(curl -s -X POST "$BASE_URL/auth/register/student" \
  -H "Content-Type: application/json" \
  -d '{
    "id": "student-1",
    "name": "김철수",
    "email": "kim@example.com",
    "password": "password123"
  }')

echo "응답: $STUDENT_REGISTER"
STUDENT_TOKEN=$(echo $STUDENT_REGISTER | jq -r '.access_token')
echo "토큰: ${STUDENT_TOKEN:0:50}..."
echo ""

# 2. 강의 등록
echo "2. 강의 등록 중..."
ENROLL_RESULT=$(curl -s -X POST "$BASE_URL/student/enroll" \
  -H "Authorization: Bearer $STUDENT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "course_id": "course-1"
  }')

echo "응답: $ENROLL_RESULT"
echo ""

# 3. 등록한 강의 목록 조회
echo "3. 등록한 강의 목록 조회 중..."
STUDENT_COURSES=$(curl -s -X GET "$BASE_URL/student/courses" \
  -H "Authorization: Bearer $STUDENT_TOKEN")

echo "강의 목록: $STUDENT_COURSES"
echo ""

# 4. 챗봇 질의
echo "4. 챗봇 질의 중..."
CHAT_RESULT=$(curl -s -X POST "$BASE_URL/chat/ask" \
  -H "Authorization: Bearer $STUDENT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "course_id": "course-1",
    "question": "Python에서 리스트는 어떻게 사용하나요?"
  }')

echo "응답: $CHAT_RESULT"
echo ""

# 5. 대화 히스토리 포함 질의
echo "5. 대화 히스토리 포함 질의 중..."
CHAT_RESULT2=$(curl -s -X POST "$BASE_URL/chat/ask" \
  -H "Authorization: Bearer $STUDENT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "course_id": "course-1",
    "question": "그럼 딕셔너리는요?",
    "conversation_id": "student-1:course-1"
  }')

echo "응답: $CHAT_RESULT2"
echo ""

# ==================== 예시 3: 에러 처리 ====================
echo ""
echo "예시 3: 에러 처리 예시"
echo "----------------------------------------"

# 1. 인증 없이 접근 시도
echo "1. 인증 없이 강의 목록 조회 시도..."
ERROR_RESPONSE=$(curl -s -w "\nHTTP_CODE:%{http_code}" -X GET "$BASE_URL/instructor/courses")
HTTP_CODE=$(echo "$ERROR_RESPONSE" | grep "HTTP_CODE" | cut -d: -f2)
echo "HTTP 상태 코드: $HTTP_CODE"
echo ""

# 2. 잘못된 토큰으로 접근 시도
echo "2. 잘못된 토큰으로 접근 시도..."
ERROR_RESPONSE2=$(curl -s -w "\nHTTP_CODE:%{http_code}" -X GET "$BASE_URL/instructor/courses" \
  -H "Authorization: Bearer invalid-token")
HTTP_CODE2=$(echo "$ERROR_RESPONSE2" | grep "HTTP_CODE" | cut -d: -f2)
echo "HTTP 상태 코드: $HTTP_CODE2"
echo ""

echo "=========================================="
echo "모든 예시 완료!"
echo "=========================================="

