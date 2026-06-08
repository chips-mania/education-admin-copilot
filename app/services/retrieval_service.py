import logging
from dataclasses import asdict, dataclass, field
from typing import Any

from app.db.supabase_client import get_supabase_client
from app.services.embedding_service import embed_query

logger = logging.getLogger(__name__)

DEFAULT_MATCH_COUNT = 5
DEFAULT_MATCH_THRESHOLD = 0.5


@dataclass
class RetrievalResult:
    id: int
    document_id: int
    chunk_no: int
    content: str
    source_type: str
    metadata: dict[str, Any]
    similarity: float
    document_title: str
    file_name: str
    file_path: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class RetrievalResponse:
    query: str
    results: list[RetrievalResult] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "query": self.query,
            "results": [result.to_dict() for result in self.results],
        }


class RetrievalService:
    def __init__(self, client=None, match_count: int = DEFAULT_MATCH_COUNT, match_threshold: float = DEFAULT_MATCH_THRESHOLD):
        self.client = client or get_supabase_client()
        self.match_count = match_count
        self.match_threshold = match_threshold

    def search(self, query: str) -> RetrievalResponse:
        logger.info("Searching query: %s", query)
        query_embedding = embed_query(query)

        response = self.client.rpc(
            "match_documents",
            {
                "query_embedding": query_embedding,
                "match_count": self.match_count,
                "match_threshold": self.match_threshold,
            },
        ).execute()

        results = [self._parse_row(row) for row in response.data or []]
        logger.info("Found %d result(s)", len(results))

        for index, result in enumerate(results, start=1):
            logger.info(
                "Top%d similarity=%.4f file=%s chunk_no=%s",
                index,
                result.similarity,
                result.file_name,
                result.chunk_no,
            )

        return RetrievalResponse(query=query, results=results)

    @staticmethod
    def _parse_row(row: dict[str, Any]) -> RetrievalResult:
        return RetrievalResult(
            id=row["id"],
            document_id=row["document_id"],
            chunk_no=row["chunk_no"],
            content=row["content"],
            source_type=row["source_type"],
            metadata=row.get("metadata") or {},
            similarity=float(row["similarity"]),
            document_title=row["document_title"],
            file_name=row["file_name"],
            file_path=row["file_path"],
        )
