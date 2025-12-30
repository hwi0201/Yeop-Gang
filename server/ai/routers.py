from fastapi import APIRouter, Depends

from ai.config import AISettings
from ai.pipelines.rag import RAGPipeline
from ai.services.stt import transcribe_video
from api.schemas import IngestRequest, QueryRequest

router = APIRouter(prefix="", tags=["ai"])


def get_pipeline(settings: AISettings = Depends(AISettings)) -> RAGPipeline:
    return RAGPipeline(settings)


@router.post("/ingest")
def ingest(payload: IngestRequest, pipeline: RAGPipeline = Depends(get_pipeline)):
    texts: list[str] = []

    if payload.text:
        texts.append(payload.text)
    if payload.source_url:
        transcript = transcribe_video(payload.source_url)
        texts.append(transcript)

    return pipeline.ingest_texts(
        texts,
        course_id=payload.course_id,
        metadata={"course_id": payload.course_id, "instructor_id": payload.instructor_id},
    )


@router.post("/query")
def query(payload: QueryRequest, pipeline: RAGPipeline = Depends(get_pipeline)):
    return pipeline.query(payload.question, course_id=payload.course_id)

