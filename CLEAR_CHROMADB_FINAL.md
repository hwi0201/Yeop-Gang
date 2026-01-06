# ChromaDB 벡터 DB 초기화 가이드

## 📍 벡터 DB 위치
- **경로**: `server/data/chroma/`

## 🗑️ 초기화 방법

### 명령어
```bash
rm -rf server/data/chroma/
```

### 단계별 가이드

```bash
# 1. 서버 종료 (실행 중인 경우)
# 터미널에서 Ctrl+C

# 2. 벡터 DB 폴더 삭제
cd /Users/mac/Desktop/hateslop/Yeop-Gang
rm -rf server/data/chroma/

# 3. 서버 재시작
cd server
uvicorn main:app --reload

# 4. 강의 파일 재업로드
# 새로운 ID 생성 로직으로 모든 세그먼트가 개별 저장됨
```

## ⚠️ 주의사항

1. **모든 데이터 삭제**: 폴더 삭제 시 모든 저장된 강의 데이터가 사라집니다
2. **서버 종료 필수**: 서버가 실행 중이면 먼저 종료하세요
3. **재업로드 필요**: 초기화 후 강의 파일을 다시 업로드해야 합니다

## ✅ 초기화 후 효과

- 새로운 ID 생성 로직 적용
- 세그먼트별로 고유 ID로 저장 (`{course_id}-seg-{index}`)
- 더 많은 컨텍스트 검색 가능
- "일부 예시만 보고 판단" 문제 완화

