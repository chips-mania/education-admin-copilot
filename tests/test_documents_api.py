import logging
from unittest.mock import MagicMock

from fastapi.testclient import TestClient

from app.api.documents import get_document_ingest_service, get_document_list_service
from app.main import app
from app.schemas.documents import DocumentItem, DocumentListResponse, DocumentSummaryStats

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SAMPLE_FILE_NAME = "01-01-01 민원의 종류.hwpx"


def test_list_documents_with_mock_service():
    mock_service = MagicMock()
    mock_service.get_documents.return_value = DocumentListResponse(
        summary=DocumentSummaryStats(
            total_documents=1,
            total_chunks=2,
            by_source_type={"manual": 1, "law": 0, "regulation": 0, "interpretation": 0},
        ),
        recent=[
            DocumentItem(
                title="민원의 종류",
                file_name=SAMPLE_FILE_NAME,
                source_type="manual",
                chunk_count=2,
            )
        ],
        documents=[
            DocumentItem(
                title="민원의 종류",
                file_name=SAMPLE_FILE_NAME,
                source_type="manual",
                chunk_count=2,
            )
        ],
    )

    app.dependency_overrides[get_document_list_service] = lambda: mock_service
    try:
        client = TestClient(app)
        response = client.get("/documents")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["summary"]["total_documents"] == 1
    assert payload["summary"]["total_chunks"] == 2
    assert payload["documents"][0]["file_name"] == SAMPLE_FILE_NAME


def test_list_documents_integration():
    client = TestClient(app)
    response = client.get("/documents")

    logger.info("documents response=%s", response.json())
    assert response.status_code == 200
    payload = response.json()
    assert "summary" in payload
    assert "documents" in payload
    assert payload["summary"]["total_chunks"] >= 0


def test_upload_rejects_unsupported_extension():
    client = TestClient(app)
    response = client.post(
        "/documents/upload",
        files={"file": ("test.txt", b"hello", "text/plain")},
    )

    assert response.status_code == 400
