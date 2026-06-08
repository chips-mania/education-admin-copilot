import logging
from unittest.mock import MagicMock

from fastapi.testclient import TestClient

from app.api.chat import get_rag_service
from app.main import app
from app.services.rag_service import RagResponse, Source

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SAMPLE_FILE_NAME = "01-01-01 민원의 종류.hwpx"


def test_health_returns_ok():
    client = TestClient(app)
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_chat_rejects_empty_question():
    client = TestClient(app)
    response = client.post("/chat", json={"question": ""})

    assert response.status_code == 422


def test_chat_with_mock_rag_service():
    mock_service = MagicMock()
    mock_service.ask.return_value = RagResponse(
        query="민원 종류 알려줘",
        answer="민원은 일반민원과 고충민원으로 구분됩니다.",
        sources=[
            Source(
                file_name=SAMPLE_FILE_NAME,
                document_title="민원의 종류",
                chunk_no=1,
                similarity=0.62,
                file_path=f"data/raw/manuals/{SAMPLE_FILE_NAME}",
                source_type="manual",
                chapter="제1편 민원정보공개",
                section="민원의 처리",
            )
        ],
    )

    app.dependency_overrides[get_rag_service] = lambda: mock_service
    try:
        client = TestClient(app)
        response = client.post("/chat", json={"question": "민원 종류 알려줘"})
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert "민원" in payload["answer"]
    assert len(payload["sources"]) == 1
    assert payload["sources"][0]["file_name"] == SAMPLE_FILE_NAME
    mock_service.ask.assert_called_once_with("민원 종류 알려줘")


def test_chat_endpoint_returns_answer():
    client = TestClient(app)
    response = client.post("/chat", json={"question": "민원 종류 알려줘"})

    logger.info("status=%s body=%s", response.status_code, response.json())

    assert response.status_code == 200
    payload = response.json()
    assert payload["answer"].strip()
    assert len(payload["sources"]) >= 1
    assert payload["sources"][0]["file_name"] == SAMPLE_FILE_NAME
    assert any(keyword in payload["answer"] for keyword in ("민원", "법정", "고충"))
