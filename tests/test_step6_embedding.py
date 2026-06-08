import json
import logging
from pathlib import Path

from app.services.embedding_service import EMBEDDING_DIM, MODEL_NAME, embed_query, embed_text, embed_texts

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

ROOT_DIR = Path(__file__).resolve().parent.parent
SAMPLE_CHUNKS = ROOT_DIR / "data" / "processed" / "chunks" / "manual" / "01-01-01 민원의 종류.chunks.json"


def test_embedding_model_constants():
    assert MODEL_NAME == "BAAI/bge-m3"
    assert EMBEDDING_DIM == 1024


def test_embed_text_returns_1024_dimension():
    vector = embed_text("민원의 종류")

    logger.info("vector_dim=%d", len(vector))
    assert len(vector) == 1024
    assert all(isinstance(value, float) for value in vector)


def test_embed_texts_for_sample_chunks():
    payload = json.loads(SAMPLE_CHUNKS.read_text(encoding="utf-8"))
    texts = [chunk["content"] for chunk in payload["chunks"]]
    vectors = embed_texts(texts)

    assert len(vectors) == len(payload["chunks"])
    for vector in vectors:
        assert len(vector) == 1024

    logger.info("embedded %d chunks", len(vectors))


def test_embed_query_returns_1024_dimension():
    vector = embed_query("민원 종류 알려줘")
    assert len(vector) == 1024
