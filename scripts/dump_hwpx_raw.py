"""Dump HWPX paragraph/style data without classification."""

from __future__ import annotations

import json
import sys
from dataclasses import asdict, is_dataclass
from pathlib import Path

from hwpx import HwpxDocument

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _to_plain(value):
    if is_dataclass(value):
        return {key: _to_plain(val) for key, val in asdict(value).items()}
    if isinstance(value, dict):
        return {str(k): _to_plain(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_to_plain(item) for item in value]
    return value


def dump_raw(file_path: Path) -> dict:
    with HwpxDocument.open(str(file_path)) as doc:
        styles = {
            sid: _to_plain(style)
            for sid, style in sorted(doc.styles.items(), key=lambda x: int(x[0]) if str(x[0]).isdigit() else 0)
        }
        char_properties = {sid: _to_plain(cp) for sid, cp in doc.char_properties.items()}

        paragraphs = []
        for index, paragraph in enumerate(doc.paragraphs):
            text = (paragraph.text or "").strip()
            if not text:
                continue
            attribs = {k: v for k, v in paragraph.element.attrib.items()}
            style_id = attribs.get("styleIDRef") or paragraph.style_id_ref
            style = doc.style(style_id)
            char_id = style.char_pr_id_ref if style else None
            paragraphs.append(
                {
                    "index": index,
                    "attribs": attribs,
                    "text": text,
                    "style": _to_plain(style) if style else None,
                    "char_property": _to_plain(doc.char_property(char_id)) if char_id is not None else None,
                }
            )

        return {
            "file_name": file_path.name,
            "file_path": file_path.as_posix(),
            "paragraph_count": len(doc.paragraphs),
            "non_empty_paragraph_count": len(paragraphs),
            "styles": styles,
            "char_properties": char_properties,
            "paragraphs": paragraphs,
        }


def main() -> None:
    default = PROJECT_ROOT / "data/raw/manuals/제1편 민원정보공개.hwpx"
    file_path = Path(sys.argv[1]) if len(sys.argv) > 1 else default
    out_path = PROJECT_ROOT / "data/processed/manual" / f"{file_path.stem}.raw.json"

    result = dump_raw(file_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(out_path)
    print(f"paragraphs: {result['non_empty_paragraph_count']}")


if __name__ == "__main__":
    main()
