import logging
import os
from functools import lru_cache

import torch
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)

MODEL_NAME = "BAAI/bge-m3"
EMBEDDING_DIM = 1024
QUERY_PREFIX = "Represent this sentence for searching relevant passages: "
DEFAULT_EMBED_BATCH_SIZE = 16


def resolve_embedding_device() -> str:
    configured = os.getenv("EMBEDDING_DEVICE", "auto").strip().lower()
    if configured in {"", "auto"}:
        return "cuda" if torch.cuda.is_available() else "cpu"
    if configured == "cuda" and not torch.cuda.is_available():
        logger.warning("EMBEDDING_DEVICE=cuda but CUDA is unavailable; falling back to cpu")
        return "cpu"
    return configured


@lru_cache(maxsize=1)
def get_embedding_model() -> SentenceTransformer:
    device = resolve_embedding_device()
    logger.info("Loading embedding model: %s (%s)", MODEL_NAME, device)
    return SentenceTransformer(MODEL_NAME, device=device)


def get_embedding_device() -> str:
    return str(get_embedding_model().device)


def embed_text(text: str) -> list[float]:
    model = get_embedding_model()
    vector = model.encode(text, normalize_embeddings=True)
    result = vector.tolist()
    logger.info("Embedded text (%d chars) -> vector dim %d", len(text), len(result))
    return result


def embed_texts(texts: list[str], *, batch_size: int | None = None) -> list[list[float]]:
    if not texts:
        return []

    model = get_embedding_model()
    effective_batch_size = batch_size or int(os.getenv("EMBEDDING_BATCH_SIZE", DEFAULT_EMBED_BATCH_SIZE))
    vectors = model.encode(
        texts,
        batch_size=effective_batch_size,
        normalize_embeddings=True,
        show_progress_bar=len(texts) >= 8,
    )
    results = [vector.tolist() for vector in vectors]
    logger.info(
        "Embedded %d text(s) on %s (batch_size=%d) -> vector dim %d",
        len(results),
        get_embedding_device(),
        effective_batch_size,
        len(results[0]),
    )
    return results


def embed_query(query: str) -> list[float]:
    return embed_text(f"{QUERY_PREFIX}{query}")


def attach_dual_embeddings(chunks: list[dict]) -> list[dict]:
    """Build V1/V2 texts from structured fields and attach embedding vectors."""
    from app.chunking.embed_versions import (
        build_embed_text_v1,
        build_embed_text_v2_from_chunk,
    )

    if not chunks:
        return []

    v1_texts = [build_embed_text_v1(chunk["content"]) for chunk in chunks]
    v2_texts = [build_embed_text_v2_from_chunk(chunk) for chunk in chunks]

    v1_vectors = embed_texts(v1_texts)
    v2_vectors = embed_texts(v2_texts)

    for chunk, v1_vector, v2_vector in zip(chunks, v1_vectors, v2_vectors):
        chunk["embedding_v1"] = v1_vector
        chunk["embedding_v2"] = v2_vector

    return chunks
