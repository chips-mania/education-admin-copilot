import logging
from functools import lru_cache

from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)

MODEL_NAME = "BAAI/bge-m3"
EMBEDDING_DIM = 1024
QUERY_PREFIX = "Represent this sentence for searching relevant passages: "


@lru_cache(maxsize=1)
def get_embedding_model() -> SentenceTransformer:
    logger.info("Loading embedding model: %s (cpu)", MODEL_NAME)
    return SentenceTransformer(MODEL_NAME, device="cpu")


def embed_text(text: str) -> list[float]:
    model = get_embedding_model()
    vector = model.encode(text, normalize_embeddings=True)
    result = vector.tolist()
    logger.info("Embedded text (%d chars) -> vector dim %d", len(text), len(result))
    return result


def embed_texts(texts: list[str]) -> list[list[float]]:
    if not texts:
        return []

    model = get_embedding_model()
    vectors = model.encode(texts, normalize_embeddings=True)
    results = [vector.tolist() for vector in vectors]
    logger.info("Embedded %d text(s) -> vector dim %d", len(results), len(results[0]))
    return results


def embed_query(query: str) -> list[float]:
    return embed_text(f"{QUERY_PREFIX}{query}")
