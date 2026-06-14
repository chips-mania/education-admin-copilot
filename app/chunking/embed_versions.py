"""Build V1/V2 embedding texts from structured chunk fields."""

from __future__ import annotations

from typing import Any

from app.chunking.outline_chunk_service import build_context_prefix


def edition_from_chunk(chunk: dict[str, Any]) -> str:
    metadata = chunk.get("metadata") or {}
    return str(metadata.get("edition") or metadata.get("title") or "")


def build_embed_text_v1(content: str) -> str:
    return (content or "").strip()


def build_embed_text_v2(
    *,
    edition: str,
    chapter: str,
    heading: str,
    content: str,
) -> str:
    prefix = build_context_prefix(edition=edition, chapter=chapter, heading=heading)
    body = build_embed_text_v1(content)
    if not body:
        return prefix
    return f"{prefix}\n\n{body}"


def build_embed_text_v2_from_chunk(chunk: dict[str, Any]) -> str:
    return build_embed_text_v2(
        edition=edition_from_chunk(chunk),
        chapter=str(chunk.get("chapter") or ""),
        heading=str(chunk.get("heading") or ""),
        content=str(chunk.get("content") or ""),
    )
