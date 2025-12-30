# 옆강 (Yeop-Gang)

EBS 인강의 말투와 지식을 복제한 AI 챗봇 서비스. 강의 영상·스크립트·교재를 기반으로 실시간 질의응답과 타임라인 점프를 지원하는 것을 목표로 합니다.

## 👥 팀원 역할 분담 (R&R)

- **`server/ai` (Backend A - 강유영)**: RAG 파이프라인, Whisper STT, 페르소나 추출, 멀티모달 처리
- **`server/api`, `server/core` (Backend B)**: 비동기 Task 관리, 멀티 테넌트 DB, API 엔드포인트, 보안
- **`client` (Frontend)**: 강사/학생 이원화 UI, 타임라인 연동, 동적 테마

📖 **상세 협업 가이드**: [COLLABORATION_GUIDE.md](./COLLABORATION_GUIDE.md) 참고

## 디렉토리 개요
- `server/main.py`: FastAPI 엔트리포인트, ai/api 라우터 통합.
- `server/ai`: RAG 파이프라인(`pipelines/`), 벡터스토어/Whisper 스텁(`services/`), 설정(`config.py`), AI 라우터(`routers.py`).
- `server/api`: 공용 스키마(`schemas.py`), API 라우터(`routers.py`).
- `client`: Next.js 14 + Tailwind 초기 세팅, 기본 레이아웃(`app/page.tsx`), 비디오/채팅 컴포넌트.

## 빠른 시작
### Backend
```bash
cd server
python -m venv .venv && source .venv/bin/activate  # Python 3.11 권장
pip install -r requirements.txt
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

**확인 사항:**
- 서버 실행 후 http://localhost:8000/ 접속 시 JSON 응답 확인
- http://localhost:8000/docs 에서 Swagger UI 확인

### Frontend
```bash
cd client
npm install
npm run dev
```

## 환경 변수 (.env)

루트 디렉토리에 `.env` 파일을 생성하세요 (`.env.example` 파일은 현재 없음).

**필수 키:**
```
OPENAI_API_KEY=your-openai-key-here
GOOGLE_API_KEY=your-google-key-here  # 선택사항
CHROMA_DB_PATH=./data/chroma
LLM_MODEL=gpt-4o-mini
EMBEDDING_MODEL=text-embedding-3-small
DATABASE_URL=sqlite:///./data/yeopgang.db
JWT_SECRET=your-secret-key
FRONTEND_URL=http://localhost:3000
BACKEND_URL=http://localhost:8000
```

**참고:**
- `.env` 파일은 `.gitignore`에 포함되어 커밋되지 않습니다
- 설정은 `dataclass` + `os.getenv`로 로드되며, `.env` 파일 읽기 실패 시 환경 변수에서 읽습니다

## 다음 단계 제안
- Backend A: Whisper STT 연결, 임베딩/리트리버/LLM 연결, 출처 반환 개선.
- Backend B: 인증(세션/JWT), 채팅 히스토리/타임라인 저장, S3/GCS 업로드 경로 확정.
- Frontend: 실제 스트리밍 플레이어 연동, 서버 SSE/WebSocket 연결, 타임라인 점프 UI.