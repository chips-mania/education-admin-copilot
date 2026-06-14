"""CLI: outline-style HWPX chunking test."""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from app.chunking.outline_chunk_service import (  # noqa: E402
    chunk_hwpx_outline,
    summarize_outline_chunks,
)
from app.schemas.document import extract_metadata_from_path, infer_source_type  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)

DEFAULT_HWPX = ROOT_DIR / "data/raw/manuals/제1편 민원정보공개.hwpx"
CHUNKS_DIR = ROOT_DIR / "data/processed/chunks/manual"


def main() -> None:
    parser = argparse.ArgumentParser(description="Chunk HWPX by Outline 2 sections")
    parser.add_argument(
        "hwpx_path",
        nargs="?",
        default=str(DEFAULT_HWPX),
        help="Path to HWPX file",
    )
    parser.add_argument(
        "--edition",
        default=None,
        help="Edition label used in contextual embed text (default: file stem)",
    )
    parser.add_argument(
        "--preview",
        type=int,
        default=3,
        help="Number of sample chunks to print",
    )
    args = parser.parse_args()

    hwpx_path = Path(args.hwpx_path).resolve()
    edition = args.edition or hwpx_path.stem
    source_type = infer_source_type(hwpx_path, ROOT_DIR)
    metadata = extract_metadata_from_path(hwpx_path, edition, source_type)

    chunks = chunk_hwpx_outline(hwpx_path, metadata=metadata, edition=edition)
    summary = summarize_outline_chunks(chunks)

    payload = {
        "file_name": hwpx_path.name,
        "file_path": hwpx_path.relative_to(ROOT_DIR).as_posix(),
        "source_type": source_type,
        "edition": edition,
        "summary": summary,
        "chunks": [chunk.to_dict() for chunk in chunks],
    }

    output_path = CHUNKS_DIR / f"{hwpx_path.stem}.outline.chunks.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    logger.info("Saved %d chunk(s) to %s", len(chunks), output_path)
    print(json.dumps(summary, ensure_ascii=False, indent=2))

    preview_count = max(args.preview, 0)
    for chunk in chunks[:preview_count]:
        print("\n---")
        print(json.dumps(chunk.to_dict(), ensure_ascii=False, indent=2))
        print("[embed_v1]")
        print(chunk.embed_text_v1() or "(empty)")
        print("[embed_v2]")
        print(chunk.embed_text_v2(edition=edition))


if __name__ == "__main__":
    main()
