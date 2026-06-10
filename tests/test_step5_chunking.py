import json
import logging
import re
from pathlib import Path

from app.chunking import (
    MAX_EMBEDDABLE_TOKENS,
    Chunk,
    chunk_document,
    count_tokens,
    filter_embeddable_chunks,
    split_into_atomic_blocks,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

ROOT_DIR = Path(__file__).resolve().parent.parent
SAMPLE_PARSED = ROOT_DIR / "data" / "processed" / "manual" / "01-01-01 민원의 종류.json"


def test_split_preserves_html_table_as_single_block():
    parsed = json.loads(SAMPLE_PARSED.read_text(encoding="utf-8"))
    blocks = split_into_atomic_blocks(parsed["content"])

    table_blocks = [block for block in blocks if "<table>" in block.lower()]
    assert len(table_blocks) == 1
    assert "법정민원" in table_blocks[0]
    assert "질의민원" in table_blocks[0]
    assert "고충민원" in table_blocks[0]


def test_chunk_document_keeps_table_intact():
    parsed = json.loads(SAMPLE_PARSED.read_text(encoding="utf-8"))
    chunks = chunk_document(parsed["content"], metadata=parsed["metadata"])

    logger.info("chunk_count=%d", len(chunks))
    for chunk in chunks:
        logger.info("chunk_no=%d, tokens~=%d", chunk.chunk_no, len(chunk.content))

    table_chunks = [chunk for chunk in chunks if "<table>" in chunk.content.lower()]
    assert len(table_chunks) >= 1

    for table_chunk in table_chunks:
        assert table_chunk.content.lower().count("<table>") == 1
        assert "</table>" in table_chunk.content.lower()
        assert "법정민원" in table_chunk.content
        assert "질의민원" in table_chunk.content

    assert chunks[0].metadata["chapter"] == "제1편 민원정보공개"
    assert chunks[0].metadata["section"] == "민원의 처리"

    if len(chunks) > 1:
        assert "<table>" not in chunks[1].content.lower()
        assert "※ 복합민원" in chunks[1].content


def test_filter_embeddable_chunks_skips_oversized_chunks():
    small_text = "민원의 종류에 대한 짧은 설명"
    huge_text = "민원 " * 20000
    assert count_tokens(huge_text) > MAX_EMBEDDABLE_TOKENS

    chunks = [
        Chunk(chunk_no=1, content=small_text, metadata={"title": "테스트"}),
        Chunk(chunk_no=2, content=huge_text, metadata={"title": "테스트"}),
        Chunk(chunk_no=3, content="복합민원 안내", metadata={"title": "테스트"}),
    ]

    filtered = filter_embeddable_chunks(chunks)

    assert len(filtered) == 2
    assert filtered[0].chunk_no == 1
    assert filtered[1].chunk_no == 2
    assert filtered[0].content == small_text
    assert filtered[1].content == "복합민원 안내"


def test_chunk_output_format():
    parsed = json.loads(SAMPLE_PARSED.read_text(encoding="utf-8"))
    chunks = chunk_document(parsed["content"], metadata=parsed["metadata"])

    assert chunks
    payload = chunks[0].to_dict()
    assert set(payload.keys()) == {"chunk_no", "content", "metadata"}
    assert payload["chunk_no"] == 1
    assert re.search(r"[가-힣]", payload["content"])
