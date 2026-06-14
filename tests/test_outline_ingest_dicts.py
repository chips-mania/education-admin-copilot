from app.chunking.outline_chunk_service import OutlineChunk, outline_chunks_to_ingest_dicts


def test_outline_chunks_to_ingest_dicts_use_structured_fields():
    chunks = outline_chunks_to_ingest_dicts(
        [
            OutlineChunk(
                chapter="민원 개요",
                heading="민원의 정의",
                content="<u>원문</u> 본문",
            )
        ],
        edition="제1편 민원정보공개",
    )

    assert len(chunks) == 1
    item = chunks[0]
    assert item["chapter"] == "민원 개요"
    assert item["heading"] == "민원의 정의"
    assert "<" not in item["content"]
    assert "본문" in item["content"]
    assert item["metadata"]["edition"] == "제1편 민원정보공개"
    assert "chapter" not in item["metadata"]
    assert "body" not in item["metadata"]
