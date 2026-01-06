from typing import Iterable, Optional, List, Dict, Any

from ai.config import AISettings
from ai.services.vectorstore import get_chroma_client, get_collection
from ai.services.embeddings import embed_texts

try:
    from openai import OpenAI
    from openai import RateLimitError, APIError
except Exception:
    OpenAI = None  # type: ignore
    RateLimitError = None  # type: ignore
    APIError = None  # type: ignore


class RAGPipeline:
    """
    Minimal RAG pipeline scaffold.
    Backend A can extend methods to add embeddings, retrievers, and LLM calls.
    """

    def __init__(self, settings: AISettings):
        self.settings = settings
        self.client = get_chroma_client(settings)
        self.collection = get_collection(self.client, settings)

    def ingest_texts(
        self,
        texts: Iterable[str],
        *,
        course_id: str,
        metadata: Optional[dict] = None,
    ) -> dict:
        """
        Ingest texts with embeddings and course-scoped metadata.
        
        IDs are generated to be unique:
        - If metadata has segment_index: use "{course_id}-seg-{segment_index}"
        - If metadata has page_number: use "{course_id}-page-{page_number}"
        - Otherwise: use "{course_id}-doc-{i}" with auto-increment
        """
        entries = list(texts)
        if not entries:
            return {"ingested": 0}

        md = metadata or {}
        md.setdefault("course_id", course_id)

        embeddings = embed_texts(entries, self.settings)

        # Generate unique IDs based on metadata
        ids = []
        metadatas = []
        
        for i, entry in enumerate(entries):
            # Use segment_index or page_number if available for unique ID
            if md.get("segment_index") is not None:
                doc_id = f"{course_id}-seg-{md['segment_index']}"
            elif md.get("page_number") is not None:
                doc_id = f"{course_id}-page-{md['page_number']}"
            elif md.get("type") == "persona":
                doc_id = f"{course_id}-persona"
            else:
                # Fallback: use index (may cause overwrites if called multiple times)
                doc_id = f"{course_id}-doc-{i}"
            
            ids.append(doc_id)
            metadatas.append({**md, "course_id": course_id})

        self.collection.upsert(
            ids=ids,
            documents=entries,
            metadatas=metadatas,
            embeddings=embeddings,
        )
        return {"ingested": len(entries)}

    def query(
        self, 
        question: str, 
        *, 
        course_id: str, 
        k: int = 10,  # 증가: 더 많은 컨텍스트를 가져오기 위해 기본값 증가
        conversation_history: Optional[List[Dict[str, str]]] = None
    ) -> dict:
        """
        Retrieval with course_id filter + LLM synthesis.
        Supports conversation history for context-aware responses.
        
        Args:
            question: Current question
            course_id: Course identifier
            k: Number of documents to retrieve
            conversation_history: List of previous messages in format [{"role": "user", "content": "..."}, {"role": "assistant", "content": "..."}]
        """
        try:
            # 질문을 임베딩으로 변환 (ingest_texts와 동일한 방식)
            try:
                query_embeddings = embed_texts([question], self.settings)
            except ValueError as e:
                # API 할당량 초과 등 임베딩 생성 실패 시
                return {
                    "question": question,
                    "documents": [],
                    "metadatas": [],
                    "answer": f"⚠️ 임베딩 생성 중 오류가 발생했습니다: {str(e)}",
                }
            # 페르소나 프롬프트도 포함하기 위해 k+1로 검색
            results = self.collection.query(
                query_embeddings=query_embeddings,
                n_results=k + 1,  # 페르소나 프롬프트 포함을 위해 +1
                include=["documents", "metadatas", "distances"],
                where={"course_id": course_id},
            )
        except ValueError as e:
            # API 키나 할당량 관련 에러
            error_msg = str(e)
            return {
                "question": question,
                "documents": [],
                "metadatas": [],
                "answer": f"⚠️ {error_msg}",
            }
        except Exception as exc:
            # If collection dimension mismatch occurs (old collection), recreate and return placeholder
            from chromadb.errors import InvalidDimensionException

            if isinstance(exc, InvalidDimensionException):
                # Recreate collection with current embedding model name suffix
                self.collection = get_collection(self.client, self.settings)
                return {
                    "question": question,
                    "documents": [],
                    "metadatas": [],
                    "answer": "벡터 컬렉션을 재생성했습니다. 다시 질문해주세요.",
                }
            raise
        docs_all = results.get("documents", []) or [[]]
        metas_all = results.get("metadatas", []) or [[]]
        docs: List[str] = docs_all[0] if docs_all else []
        metas: List[Dict[str, Any]] = metas_all[0] if metas_all else []
        
        # 디버깅: 검색된 문서 확인
        print(f"[RAG DEBUG] course_id={course_id}, 검색된 문서 수: {len(docs)}")
        if docs:
            print(f"[RAG DEBUG] 첫 번째 문서 (처음 200자): {docs[0][:200]}")
            if metas:
                print(f"[RAG DEBUG] 첫 번째 문서 메타데이터: {metas[0]}")
            if len(docs) < 3:
                print(f"[RAG DEBUG] ⚠️ 경고: 검색된 문서가 {len(docs)}개로 적습니다. 더 많은 컨텍스트가 필요할 수 있습니다.")
        else:
            print(f"[RAG DEBUG] ⚠️ 경고: course_id={course_id}에 대한 검색 결과가 비어있습니다!")
            print(f"[RAG DEBUG] ChromaDB에 해당 course_id의 데이터가 있는지 확인하세요.")
        
        answer = self._llm_answer(
            question, 
            docs, 
            metas, 
            course_id,
            conversation_history=conversation_history
        )
        return {
            "question": question,
            "documents": docs,
            "metadatas": metas,
            "answer": answer,
        }

    def _llm_answer(
        self, 
        question: str, 
        docs: List[str], 
        metas: List[Dict[str, Any]], 
        course_id: str,
        conversation_history: Optional[List[Dict[str, str]]] = None
    ) -> str:
        """
        LLM synthesis with persona prompt and conversation history.
        Audio knowledge takes priority, GPT knowledge is supplementary.
        """
        if OpenAI is None or not self.settings.openai_api_key:
            return "LLM placeholder: OPENAI_API_KEY가 없어서 기본 답변을 반환합니다."

        context_parts = []
        persona_doc = None
        for i, doc in enumerate(docs):
            meta = metas[i] if i < len(metas) else {}
            # 페르소나 프롬프트는 컨텍스트에서 제외
            if meta.get("type") == "persona":
                persona_doc = doc
                continue
            src = meta.get("source") or meta.get("filename") or ""
            ts = meta.get("start_time")
            ctx = f"[{src} @ {ts}s] {doc}" if ts is not None else doc
            context_parts.append(ctx)
        context = "\n".join(context_parts) if context_parts else ""

        # 저장된 페르소나 프롬프트 사용 (있으면), 없으면 검색된 문서로 생성
        if persona_doc:
            persona = persona_doc
        else:
            # 페르소나 프롬프트를 찾지 못한 경우, 검색된 문서로 생성 (fallback)
            persona = self.generate_persona_prompt(course_id=course_id, sample_texts=docs)
        
        # 오디오 지식 우선, GPT 지식 보조 프롬프트
        if context:
            knowledge_instruction = (
                "⚠️ 매우 중요: 아래 '강의 컨텍스트'는 강의의 일부 내용입니다. "
                "이 컨텍스트는 전체 강의의 일부 예시나 일부분일 수 있습니다. "
                "특정 예시만 보고 강의 전체 내용을 판단하지 마세요. "
                "질문에 대한 답변은 제공된 컨텍스트 내에서 찾되, "
                "전체적인 맥락을 고려하여 답변하세요.\n\n"
                "강의 컨텍스트 (일부):\n"
                f"{context}\n\n"
                "주의: 위 컨텍스트는 강의의 일부이므로, 특정 예시만으로 전체 강의 주제를 판단하지 마세요."
            )
        else:
            # 검색 결과가 없을 때는 명확히 알려주기
            knowledge_instruction = (
                "⚠️ 경고: 강의 컨텍스트를 찾지 못했습니다. "
                "이 질문에 답하기 위해서는 해당 강의의 데이터가 벡터 DB에 인제스트되어 있어야 합니다. "
                "강의 데이터가 업로드되고 처리되었는지 확인하세요. "
                "일반적인 지식으로 답변하지 마세요. '강의 데이터를 찾을 수 없습니다'라고 답변하세요."
            )
        
        sys_prompt = (
            f"{persona}\n\n"
            "위 말투 지시사항을 정확히 따라 답변하세요.\n\n"
            f"{knowledge_instruction}\n\n"
            "답변 규칙:\n"
            "- 강의 컨텍스트의 내용을 최우선으로 사용하세요.\n"
            "- ⚠️ 제공된 컨텍스트가 강의의 일부일 수 있으므로, 특정 예시만으로 전체 강의 주제를 판단하지 마세요.\n"
            "- '이건 무슨 강의'와 같은 질문에는 제공된 컨텍스트에서 전체적인 주제와 맥락을 파악하여 답변하세요.\n"
            "- 강의 컨텍스트에 없는 내용은 일반 지식으로 보완 가능하지만, 강의 내용임을 강조하세요.\n"
            "- 모르면 모른다고 말하세요.\n"
            "- 코스 범위 밖 질문은 답하지 않습니다.\n"
            "- 이전 대화 내용도 참고하여 일관성 있게 답변하세요."
        )

        # 메시지 구성 (대화 히스토리 포함)
        messages = [{"role": "system", "content": sys_prompt}]
        
        # 대화 히스토리 추가 (최근 10개만 유지)
        if conversation_history:
            # 최근 10개 메시지만 포함 (토큰 제한 고려)
            recent_history = conversation_history[-10:] if len(conversation_history) > 10 else conversation_history
            for msg in recent_history:
                role = msg.get("role", "user")
                content = msg.get("content", "")
                if role in ["user", "assistant"] and content:
                    messages.append({"role": role, "content": content})
        
        # 현재 질문 추가
        messages.append({"role": "user", "content": question})

        client = OpenAI(api_key=self.settings.openai_api_key)
        try:
            resp = client.chat.completions.create(
                model=self.settings.llm_model,
                messages=messages,
                temperature=0.3,
            )
            return resp.choices[0].message.content
        except RateLimitError as e:
            error_msg = (
                "OpenAI API 할당량을 초과했습니다. "
                "계정의 결제 정보와 사용 한도를 확인해주세요."
            )
            print(f"ERROR [LLM]: {error_msg} (에러 코드: {e.status_code if hasattr(e, 'status_code') else '429'})")
            return f"⚠️ {error_msg}"
        except APIError as e:
            error_msg = f"OpenAI API 오류가 발생했습니다: {str(e)}"
            print(f"ERROR [LLM]: {error_msg}")
            return f"⚠️ {error_msg}"

    def generate_persona_prompt(
        self, *, course_id: str, sample_texts: list[str]
    ) -> str:
        """
        Analyze speaking style from sample texts and generate persona prompt.
        Uses LLM to extract stylistic patterns (speech patterns, tone, expressions).
        """
        if not sample_texts:
            return f"당신은 course_id={course_id} 강사의 말투를 모방한 AI입니다."
        
        if OpenAI is None or not self.settings.openai_api_key:
            # Fallback to simple prompt if API key is missing
            sample = sample_texts[0][:500] if sample_texts else ""
            return (
                f"당신은 course_id={course_id} 강사의 말투를 모방한 AI입니다. "
                f"아래 샘플을 참고하여 답변하세요:\n{sample}"
            )
        
        # Combine sample texts (up to 3000 chars to avoid token limits)
        combined_text = "\n\n".join(sample_texts)
        if len(combined_text) > 3000:
            combined_text = combined_text[:3000] + "..."
        
        # Use LLM to analyze speaking style
        client = OpenAI(api_key=self.settings.openai_api_key)
        
        analysis_prompt = f"""다음은 강사의 강의 텍스트 샘플입니다. 이 강사의 말투와 스타일을 분석해주세요.

분석할 요소:
1. 종결어미 패턴 (예: "-습니다", "-어요", "-죠", "-네요" 등)
2. 어투 (정중함, 친근함, 격식, 캐주얼 등)
3. 자주 사용하는 표현이나 습관적 말투
4. 문장 구조 (짧은 문장 vs 긴 문장)
5. 특징적인 말버릇이나 반복되는 표현

강의 샘플:
{combined_text}

분석 결과를 다음 형식으로 작성해주세요:
- 종결어미: [분석 결과]
- 어투: [분석 결과]
- 자주 사용하는 표현: [분석 결과]
- 문장 구조: [분석 결과]
- 특징: [분석 결과]

이 분석을 바탕으로 이 강사의 말투를 모방하는 방법을 요약해주세요."""
        
        try:
            resp = client.chat.completions.create(
                model=self.settings.llm_model,
                messages=[
                    {
                        "role": "system",
                        "content": "당신은 언어학자이자 스타일 분석 전문가입니다. 주어진 텍스트에서 말투와 스타일을 정확하게 분석합니다.",
                    },
                    {"role": "user", "content": analysis_prompt},
                ],
                temperature=0.3,
            )
            style_analysis = resp.choices[0].message.content
        except RateLimitError as e:
            print(f"Warning: OpenAI API 할당량 초과로 페르소나 분석 실패: {e}")
            # Fallback to simple prompt
            sample = sample_texts[0][:500] if sample_texts else ""
            return (
                f"당신은 course_id={course_id} 강사의 말투를 모방한 AI입니다. "
                f"아래 샘플을 참고하여 답변하세요:\n{sample}"
            )
        except APIError as e:
            print(f"Warning: OpenAI API 오류로 페르소나 분석 실패: {e}")
            # Fallback to simple prompt
            sample = sample_texts[0][:500] if sample_texts else ""
            return (
                f"당신은 course_id={course_id} 강사의 말투를 모방한 AI입니다. "
                f"아래 샘플을 참고하여 답변하세요:\n{sample}"
            )
            
            # Generate persona prompt based on analysis
            persona_instruction = f"""당신은 course_id={course_id} 강사의 말투와 스타일을 정확하게 모방하는 AI 챗봇입니다.

강사 말투 분석:
{style_analysis}

위 분석을 바탕으로 다음 규칙을 지켜 답변하세요:
1. 분석된 종결어미 패턴을 정확히 사용하세요
2. 분석된 어투를 일관되게 유지하세요
3. 자주 사용하는 표현이나 특징적인 말버릇을 자연스럽게 사용하세요
4. 문장 구조도 원본과 유사하게 작성하세요
5. 강사의 개성과 특징을 반영하여 친근하고 자연스러운 말투로 답변하세요"""
            
            return persona_instruction
        except Exception as e:
            error_msg = str(e)
            if "insufficient_quota" in error_msg or "quota" in error_msg.lower():
                print(f"Warning: OpenAI quota exceeded during persona analysis: {error_msg}")
            else:
                print(f"Warning: Failed to analyze persona style: {error_msg}")
            # Fallback to simple prompt
            sample = sample_texts[0][:500] if sample_texts else ""
            return (
                f"당신은 course_id={course_id} 강사의 말투를 모방한 AI입니다. "
                f"아래 샘플을 참고하여 답변하세요:\n{sample}"
            )

