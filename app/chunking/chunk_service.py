import logging
import re
from dataclasses import asdict, dataclass, field
from typing import Any

import tiktoken

logger = logging.getLogger(__name__)

CHUNK_SIZE = 700
CHUNK_OVERLAP = 100
ENCODING_NAME = "cl100k_base"

TABLE_PATTERN = re.compile(r"<table>.*?</table>", re.DOTALL | re.IGNORECASE)


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
            current_parts = overlap_parts([block])
            current_tokens = count_tokens("\n\n".join(current_parts), encoding) if current_parts else 0
            continue

        separator_tokens = count_tokens("\n\n", encoding) if current_parts else 0
        projected_tokens = current_tokens + separator_tokens + block_tokens

        if projected_tokens > chunk_size and current_parts:
            flush_chunk()
            current_parts = overlap_parts([chunks[-1].content]) if chunks else []
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
