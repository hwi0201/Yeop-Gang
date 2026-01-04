# 백엔드 A 테스트 예상 결과 가이드

## 🎯 백엔드 A가 구현해야 하는 기능

당신(백엔드 A)은 다음 3가지 핵심 기능을 구현하고 테스트해야 합니다:

1. **STT (Speech-to-Text)**: 비디오 파일 → 텍스트 변환
2. **RAG 인제스트**: 텍스트 → 벡터 DB 저장
3. **RAG 쿼리**: 질문 → 검색 + LLM 답변

---

## 📋 전체 플로우 테스트 시나리오

### Step 1: 비디오 업로드
```bash
curl -X POST "http://localhost:8000/api/upload" \
  -F "instructor_id=test-instructor-1" \
  -F "course_id=test-course-1" \
  -F "video=@/Users/mac/Desktop/hateslop/Yeop-Gang/video/testvedio_1.mp4"
```

**예상 응답:**
```json
{
  "course_id": "test-course-1",
  "instructor_id": "test-instructor-1",
  "status": "processing"
}
```

---

### Step 2: 처리 상태 확인 (30초~1분 대기 후)
```bash
curl http://localhost:8000/api/status/test-course-1
```

**예상 응답 (처리 중):**
```json
{
  "course_id": "test-course-1",
  "status": "processing",
  "progress": 0
}
```

**예상 응답 (완료):**
```json
{
  "course_id": "test-course-1",
  "status": "completed",
  "progress": 100
}
```

⚠️ **만약 계속 `processing` 상태라면:**
- 백그라운드 작업이 실패했을 수 있음
- 서버 로그 확인 필요
- STT API 호출 실패 가능성

---

### Step 3: 채팅 질의 (처리 완료 후)
```bash
curl -X POST "http://localhost:8000/api/chat/ask" \
  -H "Content-Type: application/json" \
  -d '{
    "course_id": "test-course-1",
    "question": "이 강의에서 다루는 주요 내용은 무엇인가요?",
    "session_id": "test-session-1"
  }'
```

**예상 응답 (성공):**
```json
{
  "course_id": "test-course-1",
  "session_id": "test-session-1",
  "question": "이 강의에서 다루는 주요 내용은 무엇인가요?",
  "answer": "이 강의에서는... [실제 강의 내용 기반 답변]",
  "sources": [
    {
      "text": "...",
      "start_time": 12.5,
      "end_time": 45.2,
      "source": "testvedio_1.mp4"
    }
  ]
}
```

**예상 응답 (실패 - API 키 없음):**
```json
{
  "answer": "LLM placeholder: OPENAI_API_KEY가 없어서 기본 답변을 반환합니다."
}
```

**예상 응답 (실패 - 데이터 없음):**
```json
{
  "answer": "관련 문서를 찾지 못했습니다."
}
```

---

## 🔍 각 기능별 상세 테스트

### 1. STT 테스트 (단위 테스트)

**테스트 코드:**
```python
# test_stt.py
from ai.services.stt import transcribe_video
from ai.config import AISettings

settings = AISettings()
result = transcribe_video("video/testvedio_1.mp4", settings=settings)
print(result)
```

**실행:**
```bash
cd server
source ../.venv/bin/activate
python -c "from ai.services.stt import transcribe_video; from ai.config import AISettings; import json; result = transcribe_video('video/testvedio_1.mp4', AISettings()); print(json.dumps(result, indent=2, ensure_ascii=False))"
```

**예상 결과 (성공 - OPENAI_API_KEY 있음):**
```json
{
  "text": "안녕하세요. 오늘은 수학의 기초에 대해 배워보겠습니다. 첫 번째로...",
  "segments": [
    {
      "start": 0.0,
      "end": 5.2,
      "text": "안녕하세요. 오늘은 수학의 기초에 대해 배워보겠습니다."
    },
    {
      "start": 5.2,
      "end": 12.5,
      "text": "첫 번째로..."
    }
  ]
}
```

**예상 결과 (실패 - OPENAI_API_KEY 없음):**
```json
{
  "text": "Transcription placeholder. Whisper STT not available; please set OPENAI_API_KEY to enable real transcription.",
  "segments": []
}
```

---

### 2. RAG 인제스트 테스트

**테스트 코드:**
```python
# test_ingest.py
from ai.pipelines.rag import RAGPipeline
from ai.config import AISettings

settings = AISettings()
pipeline = RAGPipeline(settings)

# 테스트 텍스트 인제스트
result = pipeline.ingest_texts(
    ["안녕하세요. 오늘은 수학의 기초에 대해 배워보겠습니다."],
    course_id="test-course-1",
    metadata={"course_id": "test-course-1", "instructor_id": "test-1"}
)
print(result)
```

**실행:**
```bash
cd server
source ../.venv/bin/activate
python -c "from ai.pipelines.rag import RAGPipeline; from ai.config import AISettings; p = RAGPipeline(AISettings()); print(p.ingest_texts(['테스트 텍스트'], course_id='test-1', metadata={'course_id': 'test-1'}))"
```

**예상 결과:**
```json
{
  "ingested": 1
}
```

⚠️ **주의**: 
- OPENAI_API_KEY가 있어야 임베딩 생성 가능
- API 키 없으면 `embed_texts()` 함수에서 오류 발생

---

### 3. RAG 쿼리 테스트

**테스트 코드:**
```python
# test_query.py
from ai.pipelines.rag import RAGPipeline
from ai.config import AISettings

settings = AISettings()
pipeline = RAGPipeline(settings)

# 먼저 텍스트 인제스트
pipeline.ingest_texts(
    ["안녕하세요. 오늘은 수학의 기초에 대해 배워보겠습니다. 첫 번째로 덧셈과 뺄셈을 배워봅시다."],
    course_id="test-course-1"
)

# 질의
result = pipeline.query("수학 기초에서 배우는 내용은?", course_id="test-course-1")
print(result)
```

**실행:**
```bash
cd server
source ../.venv/bin/activate
python -c "
from ai.pipelines.rag import RAGPipeline
from ai.config import AISettings
import json

p = RAGPipeline(AISettings())
p.ingest_texts(['안녕하세요. 오늘은 수학의 기초에 대해 배워보겠습니다. 덧셈과 뺄셈을 배워봅시다.'], course_id='test-1')
result = p.query('수학 기초에서 배우는 내용은?', course_id='test-1')
print(json.dumps(result, indent=2, ensure_ascii=False))
"
```

**예상 결과 (성공 - OPENAI_API_KEY 있음 + 데이터 있음):**
```json
{
  "question": "수학 기초에서 배우는 내용은?",
  "documents": [
    "안녕하세요. 오늘은 수학의 기초에 대해 배워보겠습니다. 덧셈과 뺄셈을 배워봅시다."
  ],
  "metadatas": [
    {
      "course_id": "test-1"
    }
  ],
  "answer": "이 강의에서는 수학의 기초, 특히 덧셈과 뺄셈에 대해 배웁니다."
}
```

**예상 결과 (실패 - OPENAI_API_KEY 없음):**
```json
{
  "question": "수학 기초에서 배우는 내용은?",
  "documents": [],
  "metadatas": [],
  "answer": "LLM placeholder: OPENAI_API_KEY가 없어서 기본 답변을 반환합니다."
}
```

---

## ✅ 체크리스트: 제대로 구현되었는지 확인

### STT 구현 확인
- [ ] `transcribe_video()` 함수가 실제 OpenAI Whisper API를 호출하는가?
- [ ] API 키가 있을 때 실제 텍스트가 반환되는가?
- [ ] `segments` 배열에 타임스탬프가 포함되는가?
- [ ] API 키가 없을 때 적절한 플레이스홀더를 반환하는가?

### RAG 인제스트 확인
- [ ] `ingest_texts()` 함수가 텍스트를 임베딩으로 변환하는가?
- [ ] ChromaDB에 문서가 저장되는가?
- [ ] 메타데이터(`course_id`, `start_time`, `end_time` 등)가 저장되는가?
- [ ] `course_id`로 필터링 가능한가?

### RAG 쿼리 확인
- [ ] `query()` 함수가 벡터 검색을 수행하는가?
- [ ] `course_id`로 필터링된 결과만 반환하는가?
- [ ] LLM이 컨텍스트를 사용해 답변을 생성하는가?
- [ ] 소스 정보(타임스탬프, 파일명)가 포함되는가?

---

## 🚨 문제 진단

### 문제 1: STT가 placeholder만 반환
**원인**: OPENAI_API_KEY가 없거나 잘못됨
**해결**: `.env` 파일 확인, 서버 재시작

### 문제 2: RAG 쿼리가 "관련 문서를 찾지 못했습니다" 반환
**원인**: 
- 아직 인제스트가 안 됨 (업로드 → 처리 완료 안 됨)
- `course_id` 불일치
- ChromaDB 컬렉션이 비어있음

**해결**:
1. 업로드 후 상태 확인 (`/api/status/{course_id}`)
2. `course_id` 일치 확인
3. ChromaDB 데이터 확인

### 문제 3: LLM 답변이 placeholder
**원인**: OPENAI_API_KEY가 없음
**해결**: `.env` 파일 확인, 서버 재시작

### 문제 4: 업로드 후 계속 "processing" 상태
**원인**: 백그라운드 작업 실패
**해결**:
1. 서버 로그 확인 (터미널 출력)
2. STT API 호출 실패 가능성 확인
3. 임베딩 API 호출 실패 가능성 확인

---

## 📊 성공 기준

다음이 모두 성공하면 백엔드 A 구현 완료:

1. ✅ 비디오 업로드 → 1분 내 "completed" 상태
2. ✅ STT 결과에 실제 텍스트와 segments 포함
3. ✅ ChromaDB에 데이터 저장 확인
4. ✅ 질의 시 강의 내용 기반 답변 반환
5. ✅ 답변에 소스 정보(타임스탬프) 포함

---

## 🧪 실제 테스트 실행

현재 서버가 실행 중이라면, 다음 명령어로 바로 테스트해보세요:

```bash
# 1. 업로드
curl -X POST "http://localhost:8000/api/upload" \
  -F "instructor_id=test-1" \
  -F "course_id=test-course-1" \
  -F "video=@/Users/mac/Desktop/hateslop/Yeop-Gang/video/testvedio_1.mp4"

# 2. 1분 대기 후 상태 확인
sleep 60
curl http://localhost:8000/api/status/test-course-1

# 3. 질의
curl -X POST "http://localhost:8000/api/chat/ask" \
  -H "Content-Type: application/json" \
  -d '{"course_id": "test-course-1", "question": "이 강의의 주제는?", "session_id": "test-1"}'
```

각 단계별 결과를 확인하고, 위의 "예상 결과"와 비교해보세요!

