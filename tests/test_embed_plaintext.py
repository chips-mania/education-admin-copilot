from app.chunking.embed_plaintext import to_embed_plaintext
from app.chunking.outline_chunk_service import OutlineChunk, build_context_prefix


def test_to_embed_plaintext_strips_br_and_inline_tags():
    raw = '항목: <u><span style="color:#800080">납입독촉</span></u>, <u><span style="color:#800080">불납결손처분</span></u>'
    plain = to_embed_plaintext(raw)
    assert "<" not in plain
    assert "납입독촉" in plain
    assert "불납결손처분" in plain


def test_build_context_prefix_strips_html_from_heading():
    prefix = build_context_prefix(
        edition="제11편 학교회계 수입",
        chapter="수익자부담수입",
        heading='<u><span style="color:#800080">납입독촉</span></u>, <u><span style="color:#800080">불납결손처분</span></u>',
    )
    assert "<" not in prefix
    assert "납입독촉" in prefix
    assert "불납결손처분" in prefix


def test_outline_chunk_embed_v2_has_no_html_in_prefix():
    chunk = OutlineChunk(
        chapter="수익자부담수입",
        heading='<u><span style="color:#800080">납입독촉</span></u>',
        content="수입관리 〉 징수결의",
    )
    embed_v2 = chunk.embed_text_v2(edition="제11편 학교회계 수입")
    assert "<" not in embed_v2
    assert "납입독촉" in embed_v2
