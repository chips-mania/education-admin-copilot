import json
import logging
from pathlib import Path

from app.db.repositories import DocumentRepository

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

ROOT_DIR = Path(__file__).resolve().parent.parent
SAMPLE_EMBEDDINGS = (
    ROOT_DIR / "data" / "processed" / "embeddings" / "manual" / "01-01-01 민원의 종류.embeddings.json"
)


def test_ingest_embedding_document_to_supabase():
    payload = json.loads(SAMPLE_EMBEDDINGS.read_text(encoding="utf-8"))
    repository = DocumentRepository()

    result = repository.ingest_embedding_document(payload, replace=True)

    logger.info("ingest_result=%s", result)

    assert result["expected_chunks"] == len(payload["chunks"])
    assert result["inserted_chunks"] == len(payload["chunks"])
    assert result["stored_chunks"] == len(payload["chunks"])
    assert result["document_id"] > 0


def test_chunks_exist_in_supabase_after_ingest():
    payload = json.loads(SAMPLE_EMBEDDINGS.read_text(encoding="utf-8"))
    repository = DocumentRepository()

    result = repository.ingest_embedding_document(payload, replace=True)
    response = (
        repository.client.table("chunks")
        .select("id, chunk_no, document_id, metadata", count="exact")
        .eq("document_id", result["document_id"])
        .order("chunk_no")
        .execute()
    )

    logger.info("stored_chunks=%s", response.count)
    assert response.count == len(payload["chunks"])
    assert response.data[0]["metadata"]["chapter"] == "제1편 민원정보공개"
