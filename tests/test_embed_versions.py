from app.chunking.embed_versions import (
    build_embed_text_v1,
    build_embed_text_v2,
    build_embed_text_v2_from_chunk,
)


def test_build_embed_text_v1_is_plain_content():
    assert build_embed_text_v1("  본문 텍스트  ") == "본문 텍스트"


def test_build_embed_text_v2_adds_breadcrumb():
    text = build_embed_text_v2(
        edition="제1편 민원정보공개",
        chapter="민원 개요",
        heading="민원의 정의",
        content="민원인이 행정기관에 청구하는 것",
    )
    assert text.startswith("교육청행정업무매뉴얼 > 제1편 민원정보공개 > 민원 개요 > 민원의 정의")
    assert "민원인이 행정기관에 청구하는 것" in text


def test_build_embed_text_v2_from_chunk_uses_structured_fields():
    chunk = {
        "chapter": "민원 개요",
        "heading": "민원의 정의",
        "content": "본문",
        "metadata": {"edition": "제1편 민원정보공개"},
    }
    text = build_embed_text_v2_from_chunk(chunk)
    assert "민원 개요" in text
    assert "본문" in text
