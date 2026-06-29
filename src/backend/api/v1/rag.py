"""Composite RAG retrieval API routes."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field

from src.data.rag.answer import answer_query, build_extractive_answer, clean_answer_text
from src.data.rag.indexer import DEFAULT_INDEX_PATH, query_index

router = APIRouter(prefix="/rag", tags=["rag"])


class RagSearchResult(BaseModel):
    score: float
    title: str
    text: str
    source_kind: str
    source_id: str
    source_path: str = ""
    url: str = ""
    topic: str
    tags: list[str] = Field(default_factory=list)
    chunk_id: str
    chunk_index: int


class RagSearchResponse(BaseModel):
    query: str
    index_path: str
    result_count: int
    results: list[RagSearchResult]


class RagAnswerRequest(BaseModel):
    query: str = Field(..., min_length=2)
    top_k: int = Field(5, ge=1, le=10)
    use_llm: bool = True
    language: str = Field("auto", pattern="^(auto|ko|en)$")
    prediction_context: dict[str, Any] | None = None


class RagCitationResponse(BaseModel):
    index: int
    title: str
    source_id: str
    source_kind: str
    source: str
    score: float
    topic: str
    chunk_id: str
    excerpt: str


class RagAnswerResponse(BaseModel):
    query: str
    answer: str
    provider: str
    model: str
    citations: list[RagCitationResponse]
    retrieval_count: int
    used_llm: bool
    error: str = ""


@router.get("/search", response_model=RagSearchResponse, summary="Search the Composite RAG index")
async def search_rag(
    q: str = Query(..., min_length=2, description="Composite-domain search query"),
    top_k: int = Query(5, ge=1, le=20),
) -> RagSearchResponse:
    index_path = Path(DEFAULT_INDEX_PATH)
    if not index_path.exists():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"RAG index not found. Build it with: python scripts/rag_build_knowledge_index.py",
        )

    results = query_index(index_path, q, top_k=top_k)
    return RagSearchResponse(
        query=q,
        index_path=str(index_path),
        result_count=len(results),
        results=[
            RagSearchResult(
                score=round(result.score, 6),
                title=result.chunk.title,
                text=result.chunk.text,
                source_kind=result.chunk.source_kind,
                source_id=result.chunk.source_id,
                source_path=result.chunk.source_path,
                url=result.chunk.url,
                topic=result.chunk.topic,
                tags=result.chunk.tags,
                chunk_id=result.chunk.chunk_id,
                chunk_index=result.chunk.chunk_index,
            )
            for result in results
        ],
    )


@router.post("/answer", response_model=RagAnswerResponse, summary="Answer with Composite RAG context")
async def answer_rag(payload: RagAnswerRequest) -> RagAnswerResponse:
    index_path = Path(DEFAULT_INDEX_PATH)
    if not index_path.exists():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"RAG index not found. Build it with: python scripts/rag_build_knowledge_index.py",
        )

    try:
        answer = answer_query(
            payload.query,
            index_path=index_path,
            top_k=payload.top_k,
            use_llm=payload.use_llm,
            language=payload.language,
            prediction_context=payload.prediction_context,
        )
    except Exception as exc:
        fallback = build_extractive_answer(
            payload.query,
            [],
            language=payload.language,
            prediction_context=payload.prediction_context,
        )
        return RagAnswerResponse(
            query=payload.query,
            answer=clean_answer_text(fallback),
            provider="extractive",
            model="local-error-fallback",
            citations=[],
            retrieval_count=0,
            used_llm=False,
            error=f"RAG answer failed; used local fallback. {type(exc).__name__}: {exc}",
        )
    return RagAnswerResponse(
        query=answer.query,
        answer=clean_answer_text(answer.answer),
        provider=answer.provider,
        model=answer.model,
        citations=[RagCitationResponse(**citation.to_dict()) for citation in answer.citations],
        retrieval_count=answer.retrieval_count,
        used_llm=answer.used_llm,
        error=answer.error,
    )
