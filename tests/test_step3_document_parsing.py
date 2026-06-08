import json
import logging
import re
from pathlib import Path

from app.parsers import parse_document
from app.parsers.hwpx_parser import parse_hwpx

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

ROOT_DIR = Path(__file__).resolve().parent.parent
SAMPLE_HWPX = ROOT_DIR / "data" / "raw" / "manuals" / "01-01-01 민원의 종류.hwpx"


def test_parse_hwpx_extracts_korean_text():
    parsed = parse_hwpx(SAMPLE_HWPX, project_root=ROOT_DIR)

    logger.info("title=%s", parsed.title)
    logger.info("source_type=%s", parsed.source_type)
    logger.info("metadata=%s", parsed.metadata)
    logger.info("content_length=%d", len(parsed.content))
    logger.info("content_preview=%s", parsed.content[:300])

    assert parsed.title == "민원의 종류"
    assert parsed.source_type == "manual"
    assert parsed.file_name == "01-01-01 민원의 종류.hwpx"
    assert "data/raw/manuals/" in parsed.file_path
    assert parsed.metadata["chapter"] == "제1편 민원정보공개"
    assert parsed.metadata["section"] == "민원의 처리"
    assert parsed.metadata["title"] == "민원의 종류"
    assert parsed.metadata["item_no"] == "1"
    assert parsed.metadata["source"] == "업무매뉴얼"
    assert len(parsed.content) > 100
    assert re.search(r"[가-힣]", parsed.content)
    assert "법정민원" in parsed.content
    assert "<table>" in parsed.content or "|" in parsed.content


def test_parse_hwpx_preserves_table_structure():
    parsed = parse_hwpx(SAMPLE_HWPX, project_root=ROOT_DIR)

    assert "구 분" in parsed.content
    assert "내  용" in parsed.content or "내 용" in parsed.content
    assert "질의민원" in parsed.content
    assert "법령⋅훈령" in parsed.content or "법령" in parsed.content


def test_parse_document_router_hwpx():
    parsed = parse_document(SAMPLE_HWPX, project_root=ROOT_DIR)
    assert parsed.title == "민원의 종류"
    assert parsed.source_type == "manual"


def test_parse_documents_script_output_format(tmp_path):
    parsed = parse_hwpx(SAMPLE_HWPX, project_root=ROOT_DIR)
    payload = parsed.to_dict()

    output_path = tmp_path / "sample.json"
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    loaded = json.loads(output_path.read_text(encoding="utf-8"))
    assert set(loaded.keys()) == {
        "title",
        "content",
        "source_type",
        "file_name",
        "file_path",
        "metadata",
    }
    assert loaded["title"] == "민원의 종류"
    assert loaded["source_type"] == "manual"
