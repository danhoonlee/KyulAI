"""RAG source collection utilities for composite-domain knowledge bases."""

from src.data.rag.answer import RagAnswer, RagCitation, answer_query
from src.data.rag.collector import CollectionResult, collect_sources
from src.data.rag.indexer import KnowledgeChunk, QueryResult, build_knowledge_index, query_index
from src.data.rag.sources import RagSource, load_sources

__all__ = [
    "CollectionResult",
    "KnowledgeChunk",
    "QueryResult",
    "RagAnswer",
    "RagCitation",
    "RagSource",
    "answer_query",
    "build_knowledge_index",
    "collect_sources",
    "load_sources",
    "query_index",
]
