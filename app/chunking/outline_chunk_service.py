"""Structure-aware chunking for HWPX manuals using Outline styles."""

from __future__ import annotations

import logging
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from hwpx import HwpxDocument
from hwpx.tools.markdown_export import _p_element_to_md, _table_to_md

from app.chunking.chunk_service import Chunk, count_tokens
from app.chunking.embed_plaintext import to_embed_plaintext

logger = logging.getLogger(__name__)

OUTLINE_LEVEL_BY_NAME = {
    "outline 1": 1,
    "outline 2": 2,
    "outline 3": 3,
    "outline 4": 4,
    "outline 5": 5,
    "outline 6": 6,
    "outline 7": 7,
    "개요 1": 1,
    "개요 2": 2,
    "개요 3": 3,
    "개요 4": 4,
    "개요 5": 5,
    "개요 6": 6,
    "개요 7": 7,
}

BODY_STYLE_NAMES = {"바탕글", "바탕글 사본2"}
BODY_STYLE_ENG = {"normal", "normal copy2"}

MANUAL_ROOT = "교육청행정업무매뉴얼"


def _plain_outline_text(text: str) -> str:
    if not text or not text.strip():
        return ""
    plain = to_embed_plaintext(text)
    return " ".join(line.strip() for line in plain.split("\n") if line.strip())


def build_context_prefix(*, edition: str, chapter: str, heading: str) -> str:
    parts = (
        MANUAL_ROOT,
        _plain_outline_text(edition),
        _plain_outline_text(chapter),
        _plain_outline_text(heading),
    )
    return " > ".join(part for part in parts if part)


@dataclass
class OutlineChunk:
    chapter: str
    heading: str
    content: str
    table: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        payload = {
            "chapter": self.chapter,
            "heading": self.heading,
            "content": self.content,
            "table": self.table,
        }
        if self.metadata:
            payload["metadata"] = dict(self.metadata)
        return payload

    def embed_body(self) -> str:
        parts: list[str] = []
        if self.content.strip():
            plain = to_embed_plaintext(self.content)
            if plain:
                parts.append(plain)
        if self.table and self.table.strip():
            plain_table = to_embed_plaintext(self.table)
            if plain_table:
                parts.append(plain_table)

        body = "\n\n".join(parts).strip()
        if body:
            return body
        return _plain_outline_text(self.heading)

    def embed_text_v1(self) -> str:
        return self.embed_body()

    def embed_text_v2(self, *, edition: str | None = None) -> str:
        edition_name = edition or self.metadata.get("edition") or self.metadata.get("title", "")
        prefix = build_context_prefix(
            edition=edition_name,
            chapter=self.chapter,
            heading=self.heading,
        )
        body = self.embed_body()
        if not body:
            return prefix
        return f"{prefix}\n\n{body}"


def outline_level(style) -> int | None:
    if style is None:
        return None
    for key in (style.eng_name or "", style.name or ""):
        normalized = key.strip().lower()
        if normalized in OUTLINE_LEVEL_BY_NAME:
            return OUTLINE_LEVEL_BY_NAME[normalized]
    name = (style.name or "").strip()
    match = re.match(r"^(?:개요|제목)\s*(\d+)$", name)
    if match:
        return int(match.group(1))
    match = re.match(r"^outline\s*(\d+)$", (style.eng_name or "").strip(), re.I)
    if match:
        return int(match.group(1))
    if name in BODY_STYLE_NAMES or (style.eng_name or "").strip().lower() in BODY_STYLE_ENG:
        return 0
    return None


def _paragraph_text(paragraph, doc: HwpxDocument) -> str:
    md = _p_element_to_md(paragraph.element, doc, None).strip()
    if md and paragraph.tables:
        plain = (paragraph.text or "").strip()
        all_cell_text = "".join(
            (cell.text or "")
            for table in paragraph.tables
            for row in table.rows
            for cell in row.cells
        )
        if plain and plain in all_cell_text:
            md = ""
    if md:
        return md
    return (paragraph.text or "").strip()


def _paragraph_tables(paragraph, doc: HwpxDocument) -> list[str]:
    tables = [_table_to_md(table, doc, {}, 0, None) for table in paragraph.tables]
    return [table.strip() for table in tables if table and table.strip()]


def _append_tables(target: list[str], tables: list[str]) -> None:
    for table in tables:
        if table and (not target or target[-1] != table):
            target.append(table)


def _join_tables(tables: list[str]) -> str | None:
    if not tables:
        return None
    return "\n\n".join(tables)


def _join_content(lines: list[str]) -> str:
    return "\n\n".join(line for line in lines if line.strip())


def chunk_hwpx_outline(
    file_path: Path,
    *,
    metadata: dict[str, Any] | None = None,
    edition: str | None = None,
) -> list[OutlineChunk]:
    file_path = file_path.resolve()
    logger.info("Outline chunking HWPX: %s", file_path)

    with HwpxDocument.open(str(file_path)) as doc:
        return _chunk_open_document(doc, metadata=metadata, edition=edition)


def _chunk_open_document(
    doc: HwpxDocument,
    *,
    metadata: dict[str, Any] | None = None,
    edition: str | None = None,
) -> list[OutlineChunk]:
    base_metadata = dict(metadata or {})
    if edition:
        base_metadata.setdefault("edition", edition)

    chapter = ""
    chapter_tables: list[str] = []
    current: dict[str, Any] | None = None
    chunks: list[OutlineChunk] = []

    def flush_current() -> None:
        nonlocal current
        if current is None:
            return
        chunk = OutlineChunk(
            chapter=_plain_outline_text(current["chapter"]),
            heading=_plain_outline_text(current["heading"]),
            content=_join_content(current["content_lines"]),
            table=_join_tables(current["tables"]),
            metadata=dict(base_metadata),
        )
        chunks.append(chunk)
        current = None

    def ensure_current(heading: str) -> None:
        nonlocal current, chapter_tables
        if current is not None and current["heading"] == heading:
            return
        flush_current()
        tables = list(chapter_tables)
        chapter_tables = []
        current = {
            "chapter": chapter,
            "heading": heading,
            "content_lines": [],
            "tables": tables,
        }

    def attach_tables(tables: list[str]) -> None:
        nonlocal chapter_tables
        if not tables:
            return
        if current is not None:
            _append_tables(current["tables"], tables)
        elif chapter:
            _append_tables(chapter_tables, tables)

    for section in doc.sections:
        for paragraph in section.paragraphs:
            style = doc.style(paragraph.style_id_ref)
            level = outline_level(style)
            text = _paragraph_text(paragraph, doc)
            tables = _paragraph_tables(paragraph, doc)

            if level == 1 and text:
                flush_current()
                chapter = _plain_outline_text(text)
                chapter_tables = []
                if tables:
                    _append_tables(chapter_tables, tables)
                continue

            if level == 2 and text:
                ensure_current(_plain_outline_text(text))
                if tables:
                    attach_tables(tables)
                continue

            if level in {3, 4, 0} and text:
                if current is None:
                    logger.debug("Skipping orphan body paragraph: %s", text[:60])
                else:
                    current["content_lines"].append(text)
                if tables:
                    attach_tables(tables)
                continue

            if text:
                if current is not None:
                    current["content_lines"].append(text)
                else:
                    logger.debug("Skipping unclassified paragraph: %s", text[:60])
            if tables:
                attach_tables(tables)

    flush_current()
    logger.info("Outline chunking complete: %d chunk(s)", len(chunks))
    return chunks


def outline_chunks_to_ingest_dicts(
    outline_chunks: list[OutlineChunk],
    *,
    edition: str,
) -> list[dict[str, Any]]:
    chunks: list[dict[str, Any]] = []
    for index, outline_chunk in enumerate(outline_chunks, start=1):
        metadata = dict(outline_chunk.metadata)
        metadata["edition"] = edition
        if outline_chunk.table:
            metadata["table"] = outline_chunk.table

        chunks.append(
            {
                "chunk_no": index,
                "chapter": outline_chunk.chapter,
                "heading": outline_chunk.heading,
                "content": outline_chunk.embed_body(),
                "metadata": metadata,
            }
        )
    return chunks


def outline_chunks_to_legacy_chunks(
    outline_chunks: list[OutlineChunk],
    *,
    metadata: dict[str, Any] | None = None,
) -> list[Chunk]:
    legacy: list[Chunk] = []
    for index, outline_chunk in enumerate(outline_chunks, start=1):
        chunk_metadata = dict(metadata or {})
        chunk_metadata.update(
            {
                "chapter": outline_chunk.chapter,
                "heading": outline_chunk.heading,
            }
        )
        if outline_chunk.table:
            chunk_metadata["table"] = outline_chunk.table
        legacy.append(
            Chunk(
                chunk_no=index,
                content=outline_chunk.embed_text_v1(),
                metadata=chunk_metadata,
            )
        )
    return legacy


def summarize_outline_chunks(outline_chunks: list[OutlineChunk]) -> dict[str, Any]:
    token_counts = [count_tokens(chunk.embed_text_v1()) for chunk in outline_chunks]
    table_counts = sum(1 for chunk in outline_chunks if chunk.table)
    return {
        "chunk_count": len(outline_chunks),
        "chunks_with_table": table_counts,
        "token_min": min(token_counts) if token_counts else 0,
        "token_max": max(token_counts) if token_counts else 0,
        "token_avg": round(sum(token_counts) / len(token_counts), 1) if token_counts else 0,
    }
