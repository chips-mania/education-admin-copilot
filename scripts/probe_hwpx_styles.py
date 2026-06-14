"""Probe python-hwpx style/paragraph APIs on a sample HWPX file."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from hwpx import HwpxDocument

PROJECT_ROOT = Path(__file__).resolve().parents[1]

OUTLINE_LEVEL = {
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
    "제목 1": 1,
    "제목 2": 2,
    "제목 3": 3,
    "제목 4": 4,
}


def heading_level(style) -> int | None:
    if style is None:
        return None
    for key in (style.eng_name or "", style.name or ""):
        normalized = key.strip().lower()
        if normalized in OUTLINE_LEVEL:
            return OUTLINE_LEVEL[normalized]
    name = (style.name or "").strip()
    match = re.match(r"^(?:개요|제목)\s*(\d+)$", name)
    if match:
        return int(match.group(1))
    match = re.match(r"^outline\s*(\d+)$", (style.eng_name or "").strip(), re.I)
    if match:
        return int(match.group(1))
    return None


def classify_paragraph(doc: HwpxDocument, paragraph) -> dict:
    style_id = paragraph.style_id_ref
    style = doc.style(style_id)
    level = heading_level(style)
    text = (paragraph.text or "").strip()
    if level is not None and text:
        block_type = "heading"
    else:
        block_type = "paragraph"
    return {
        "type": block_type,
        "level": level,
        "text": text,
        "style_id": str(style_id) if style_id is not None else None,
        "style_name": style.name if style else None,
        "style_eng_name": style.eng_name if style else None,
        "para_pr_id": str(paragraph.para_pr_id_ref) if paragraph.para_pr_id_ref is not None else None,
    }


def probe(file_path: Path, *, search: str | None = None, limit: int = 50) -> dict:
    with HwpxDocument.open(str(file_path)) as doc:
        styles = []
        for sid, style in sorted(doc.styles.items(), key=lambda x: int(x[0]) if str(x[0]).isdigit() else 0):
            styles.append(
                {
                    "id": sid,
                    "name": style.name,
                    "eng_name": style.eng_name,
                    "type": style.type,
                    "heading_level": heading_level(style),
                    "para_pr_id_ref": style.para_pr_id_ref,
                    "char_pr_id_ref": style.char_pr_id_ref,
                }
            )

        blocks: list[dict] = []
        matches: list[dict] = []
        for paragraph in doc.paragraphs:
            block = classify_paragraph(doc, paragraph)
            if not block["text"]:
                continue
            blocks.append(block)
            if search and search in block["text"]:
                matches.append(block)

        return {
            "file": str(file_path),
            "paragraph_count": len(list(doc.paragraphs)),
            "non_empty_blocks": len(blocks),
            "styles": styles,
            "sample_blocks": blocks[:limit],
            "search": search,
            "search_matches": matches,
        }


def main() -> None:
    default = PROJECT_ROOT / "data/raw/manuals/제1편 민원정보공개.hwpx"
    file_path = Path(sys.argv[1]) if len(sys.argv) > 1 else default
    search = sys.argv[2] if len(sys.argv) > 2 else "민원의 정의"
    out_path = PROJECT_ROOT / "data/processed/manual/_probe_hwpx_styles.json"

    result = probe(file_path, search=search)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote probe result to {out_path}")
    print(f"Styles: {len(result['styles'])}, blocks sampled: {len(result['sample_blocks'])}")
    print(f"Search '{search}' matches: {len(result['search_matches'])}")
    for match in result["search_matches"][:5]:
        print(json.dumps(match, ensure_ascii=False))


if __name__ == "__main__":
    main()
