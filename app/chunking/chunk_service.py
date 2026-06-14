import logging
import re
from dataclasses import asdict, dataclass, field
from typing import Any

import tiktoken

logger = logging.getLogger(__name__)

CHUNK_SIZE = 700
CHUNK_OVERLAP = 100
MAX_EMBEDDABLE_TOKENS = 10000
ENCODING_NAME = "cl100k_base"

TABLE_PATTERN = re.compile(r"<table>.*?</table>", re.DOTALL | re.IGNORECASE)


def _contains_table(text: str) -> bool:
    return "<table>" in text.lower()


@dataclass
class Chunk:
    chunk_no: int
    content: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def count_tokens(text: str, encoding: tiktoken.Encoding | None = None) -> int:
    enc = encoding or tiktoken.get_encoding(ENCODING_NAME)
    return len(enc.encode(text))


def filter_embeddable_chunks(chunks: list[Chunk]) -> list[Chunk]:
    encoding = tiktoken.get_encoding(ENCODING_NAME)
    kept: list[Chunk] = []

    for chunk in chunks:
        token_count = count_tokens(chunk.content, encoding)
        if token_count > MAX_EMBEDDABLE_TOKENS:
            logger.warning(
                "Skipping chunk %d (%d tokens > %d limit)",
                chunk.chunk_no,
                token_count,
                MAX_EMBEDDABLE_TOKENS,
            )
            continue

        kept.append(
            Chunk(
                chunk_no=len(kept) + 1,
                content=chunk.content,
                metadata=dict(chunk.metadata),
            )
        )

    skipped = len(chunks) - len(kept)
    if skipped:
        logger.info(
            "Filtered chunks: kept %d, skipped %d (>%d tokens)",
            len(kept),
            skipped,
            MAX_EMBEDDABLE_TOKENS,
        )

    return kept


def filter_embeddable_chunk_dicts(chunks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    from app.chunking.embed_versions import build_embed_text_v1, build_embed_text_v2_from_chunk

    encoding = tiktoken.get_encoding(ENCODING_NAME)
    kept: list[dict[str, Any]] = []

    for chunk in chunks:
        content = chunk.get("content")
        if content is None:
            continue

        texts_to_check = [build_embed_text_v1(str(content))]
        v2_text = build_embed_text_v2_from_chunk(chunk)
        if v2_text and v2_text != texts_to_check[0]:
            texts_to_check.append(v2_text)

        over_limit = False
        for text in texts_to_check:
            token_count = count_tokens(text, encoding)
            if token_count > MAX_EMBEDDABLE_TOKENS:
                logger.warning(
                    "Skipping chunk %d (%d tokens > %d limit)",
                    chunk.get("chunk_no"),
                    token_count,
                    MAX_EMBEDDABLE_TOKENS,
                )
                over_limit = True
                break

        if over_limit:
            continue

        kept.append({**chunk, "chunk_no": len(kept) + 1})

    skipped = len(chunks) - len(kept)
    if skipped:
        logger.info(
            "Filtered chunks: kept %d, skipped %d (>%d tokens)",
            len(kept),
            skipped,
            MAX_EMBEDDABLE_TOKENS,
        )

    return kept


def split_into_atomic_blocks(content: str) -> list[str]:
    blocks: list[str] = []
    last_end = 0

    for match in TABLE_PATTERN.finditer(content):
        before = content[last_end : match.start()].strip()
        if before:
            blocks.extend(_split_text_blocks(before))
        blocks.append(match.group(0).strip())
        last_end = match.end()

    remaining = content[last_end:].strip()
    if remaining:
        blocks.extend(_split_text_blocks(remaining))

    if not blocks and content.strip():
        blocks.append(content.strip())

    logger.info("Split content into %d atomic block(s)", len(blocks))
    return blocks


def _split_text_blocks(text: str) -> list[str]:
    paragraphs = [part.strip() for part in re.split(r"\n{2,}", text) if part.strip()]
    if not paragraphs:
        return [text.strip()] if text.strip() else []
    return paragraphs


def chunk_document(
    content: str,
    metadata: dict[str, Any] | None = None,
    chunk_size: int = CHUNK_SIZE,
    chunk_overlap: int = CHUNK_OVERLAP,
) -> list[Chunk]:
    encoding = tiktoken.get_encoding(ENCODING_NAME)
    blocks = split_into_atomic_blocks(content)
    chunks: list[Chunk] = []
    current_parts: list[str] = []
    current_tokens = 0

    def flush_chunk() -> None:
        nonlocal current_parts, current_tokens
        if not current_parts:
            return
        chunk_text = "\n\n".join(current_parts).strip()
        chunks.append(
            Chunk(
                chunk_no=len(chunks) + 1,
                content=chunk_text,
                metadata=dict(metadata or {}),
            )
        )
        logger.info("Created chunk %d (%d tokens)", len(chunks), count_tokens(chunk_text, encoding))
        current_parts = []
        current_tokens = 0

    def overlap_parts(parts: list[str]) -> list[str]:
        if not parts or chunk_overlap <= 0:
            return []

        combined = "\n\n".join(parts)
        tokens = encoding.encode(combined)
        if len(tokens) <= chunk_overlap:
            return [combined]

        overlap_text = encoding.decode(tokens[-chunk_overlap:])
        return [overlap_text.strip()] if overlap_text.strip() else []

    for block in blocks:
        block_tokens = count_tokens(block, encoding)

        if block_tokens > chunk_size:
            flush_chunk()
            chunks.append(
                Chunk(
                    chunk_no=len(chunks) + 1,
                    content=block,
                    metadata=dict(metadata or {}),
                )
            )
            logger.info(
                "Created atomic chunk %d for oversized block (%d tokens)",
                len(chunks),
                block_tokens,
            )
            current_parts = []
            current_tokens = 0
            continue

        separator_tokens = count_tokens("\n\n", encoding) if current_parts else 0
        projected_tokens = current_tokens + separator_tokens + block_tokens

        if projected_tokens > chunk_size and current_parts:
            flush_chunk()
            if chunks and not _contains_table(chunks[-1].content):
                current_parts = overlap_parts([chunks[-1].content])
            else:
                current_parts = []
            current_tokens = count_tokens("\n\n".join(current_parts), encoding) if current_parts else 0
            separator_tokens = count_tokens("\n\n", encoding) if current_parts else 0
            projected_tokens = current_tokens + separator_tokens + block_tokens

        if current_parts:
            current_parts.append(block)
            current_tokens = projected_tokens
        else:
            current_parts = [block]
            current_tokens = block_tokens

    flush_chunk()
    logger.info("Chunking complete: %d chunk(s)", len(chunks))
    return chunks
