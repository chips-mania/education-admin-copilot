import logging
from typing import Any

from app.db.repositories import DocumentRepository
from app.schemas.documents import SOURCE_TYPES, DocumentItem, DocumentListResponse, DocumentSummaryStats

logger = logging.getLogger(__name__)

RECENT_LIMIT = 5


class DocumentListService:
    def __init__(self, repository: DocumentRepository | None = None):
        self.repository = repository or DocumentRepository()

    def get_documents(self) -> DocumentListResponse:
        rows = self.repository.list_documents()
        by_source_type = {source_type: 0 for source_type in SOURCE_TYPES}
        documents: list[DocumentItem] = []

        for row in rows:
            source_type = row["source_type"]
            if source_type in by_source_type:
                by_source_type[source_type] += 1

            documents.append(
                DocumentItem(
                    title=row["title"],
                    file_name=row["file_name"],
                    source_type=source_type,
                    chunk_count=row.get("chunk_count", 0),
                    file_path=row.get("file_path"),
                    created_at=row.get("created_at"),
                )
            )

        summary = DocumentSummaryStats(
            total_documents=len(documents),
            total_chunks=self.repository.count_all_chunks(),
            by_source_type=by_source_type,
        )
        recent = documents[:RECENT_LIMIT]

        logger.info(
            "Document summary total=%d chunks=%d",
            summary.total_documents,
            summary.total_chunks,
        )
        return DocumentListResponse(summary=summary, recent=recent, documents=documents)
