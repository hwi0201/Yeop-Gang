#!/bin/bash
# 챗봇 말투 테스트 스크립트

echo "╔══════════════════════════════════════════════════════════════╗"
echo "║         챗봇 말투 학습 검사                                   ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""
echo "테스트 질문을 보내고 답변을 확인합니다..."
echo ""

curl -X POST "http://localhost:8000/api/chat/ask" \
  -H "Content-Type: application/json" \
  -d '{
    "course_id": "test-course-1",
    "question": "안녕하세요, 간단히 자기소개 해주세요."
  }' | python3 -m json.tool

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "추가 테스트 질문..."
echo ""

curl -X POST "http://localhost:8000/api/chat/ask" \
  -H "Content-Type: application/json" \
  -d '{
    "course_id": "test-course-1",
    "question": "이 강의는 어떤 내용인가요?"
  }' | python3 -m json.tool

