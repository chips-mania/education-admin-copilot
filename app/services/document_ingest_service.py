import logging
from pathlib import Path
from typing import Any

from app.chunking import chunk_document
from app.config.settings import BASE_DIR
from app.db.repositories import DocumentRepository
from app.parsers import parse_document
from app.services.embedding_service import embed_texts

logger = logging.getLogger(__name__)

SUPPORTED_EXTENSIONS = {".hwpx", ".pdf"}
RAW_FOLDER_BY_SOURCE_TYPE = {
    "manual": "manuals",
    "law": "laws",
    "regulation": "regulations",
    "interpretation": "interpretations",
}


class DocumentIngestService:
    def __init__(self, repository: DocumentRepository | None = None, project_root: Path | None = None):
        self.repository = repository or DocumentRepository()
        self.project_root = project_root or BASE_DIR

    def ingest_uploaded_file(self, file_name: str, file_bytes: bytes, source_type: str = "manual") -> dict[str, Any]:
        suffix = Path(file_name).suffix.lower()
        if suffix not in SUPPORTED_EXTENSIONS:
            raise ValueError(f"Unsupported file type: {suffix}. Only PDF and HWPX are supported.")

        folder = RAW_FOLDER_BY_SOURCE_TYPE.get(source_type, "manuals")
        raw_dir = self.project_root / "data" / "raw" / folder
        raw_dir.mkdir(parents=True, exist_ok=True)

        file_path = raw_dir / Path(file_name).name
        file_path.write_bytes(file_bytes)
        logger.info("Saved uploaded file: %s", file_path)

        parsed = parse_document(file_path, project_root=self.project_root).to_dict()
        chunks = chunk_document(parsed["content"], metadata=parsed.get("metadata", {}))
        chunk_dicts = [chunk.to_dict() for chunk in chunks]

        vectors = embed_texts([chunk["content"] for chunk in chunk_dicts])
        for chunk, vector in zip(chunk_dicts, vectors):
            chunk["embedding"] = vector

        payload = {
            "title": parsed["title"],
            "source_type": parsed["source_type"],
            "file_name": parsed["file_name"],
            "file_path": parsed["file_path"],
            "chunks": chunk_dicts,
        }

        result = self.repository.ingest_embedding_document(payload)
        logger.info(
            "Ingested upload file=%s document_id=%s chunks=%s",
            parsed["file_name"],
            result["document_id"],
            result["stored_chunks"],
        )

        return {
            "title": parsed["title"],
            "file_name": parsed["file_name"],
            "source_type": parsed["source_type"],
            "document_id": result["document_id"],
            "chunk_count": result["stored_chunks"],
        }
