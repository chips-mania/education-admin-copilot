import logging
from dataclasses import asdict, dataclass, field
from typing import Any, Literal

from app.services.llm_service import LLMService
from app.services.retrieval_service import (
    DEFAULT_MATCH_COUNT,
    DEFAULT_MATCH_THRESHOLD,
    RetrievalResult,
    RetrievalService,
)

logger = logging.getLogger(__name__)


@dataclass
class Source:
    file_name: str
    document_title: str
    chunk_no: int
    similarity: float
    file_path: str
    source_type: str
    chapter: str | None = None
    section: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class RagResponse:
    query: str
    answer: str
    embed_version: Literal["v1", "v2"] = "v2"
    sources: list[Source] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "query": self.query,
            "answer": self.answer,
            "embed_version": self.embed_version,
            "sources": [source.to_dict() for source in self.sources],
        }


def build_sources(results: list[RetrievalResult]) -> list[Source]:
    sources: list[Source] = []
    for result in results:
        metadata = result.metadata or {}
        sources.append(
            Source(
                file_name=result.file_name,
                document_title=result.document_title,
                chunk_no=result.chunk_no,
                similarity=result.similarity,
                file_path=result.file_path,
                source_type=result.source_type,
                chapter=result.chapter or metadata.get("chapter"),
                section=result.heading or metadata.get("section"),
            )
        )
    return sources


class RagService:
    def __init__(
        self,
        llm_service: LLMService | None = None,
        match_count: int = DEFAULT_MATCH_COUNT,
        match_threshold: float = DEFAULT_MATCH_THRESHOLD,
    ):
        self.match_count = match_count
        self.match_threshold = match_threshold
        self.llm_service = llm_service or LLMService()

    def ask(self, query: str, *, embed_version: Literal["v1", "v2"] = "v2") -> RagResponse:
        logger.info("RAG query: %s (embed_version=%s)", query, embed_version)
        retrieval_service = RetrievalService(
            match_count=self.match_count,
            match_threshold=self.match_threshold,
            embed_version=embed_version,
        )
        retrieval = retrieval_service.search(query)
        answer = self.llm_service.generate_answer(query, retrieval.results)
        sources = build_sources(retrieval.results)

        logger.info("RAG completed sources=%d answer_chars=%d", len(sources), len(answer))
        return RagResponse(
            query=query,
            answer=answer,
            embed_version=embed_version,
            sources=sources,
        )
