"""Export V1/V2 embedding texts from outline chunks."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from app.chunking.embed_versions import build_embed_text_v1, build_embed_text_v2  # noqa: E402
from app.chunking.outline_chunk_service import OutlineChunk  # noqa: E402

CHUNKS_DIR = ROOT_DIR / "data/processed/chunks/manual"
EMBED_DIR = ROOT_DIR / "data/processed/embed"


def load_outline_chunks(path: Path) -> tuple[str, list[OutlineChunk]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    edition = payload.get("edition") or payload.get("file_name", "").removesuffix(".hwpx")
    chunks: list[OutlineChunk] = []
    for item in payload["chunks"]:
        metadata = dict(item.get("metadata") or {})
        metadata.setdefault("edition", edition)
        chunks.append(
            OutlineChunk(
                chapter=item["chapter"],
                heading=item["heading"],
                content=item.get("content") or "",
                table=item.get("table"),
                metadata=metadata,
            )
        )
    return edition, chunks


def export_embed_versions(chunks_path: Path, *, edition: str | None = None) -> dict[str, Path]:
    chunks_path = chunks_path.resolve()
    edition_name, chunks = load_outline_chunks(chunks_path)
    edition_name = edition or edition_name
    stem = chunks_path.stem.replace(".outline.chunks", "")
    EMBED_DIR.mkdir(parents=True, exist_ok=True)

    records = []
    v1_blocks: list[str] = []
    v2_blocks: list[str] = []

    for index, chunk in enumerate(chunks, start=1):
        body = chunk.embed_body()
        embed_v1 = build_embed_text_v1(body)
        embed_v2 = build_embed_text_v2(
            edition=edition_name,
            chapter=chunk.chapter,
            heading=chunk.heading,
            content=body,
        )
        records.append(
            {
                "chunk_no": index,
                "chapter": chunk.chapter,
                "heading": chunk.heading,
                "embed_v1": embed_v1,
                "embed_v2": embed_v2,
            }
        )
        separator = f"\n\n{'=' * 72}\n[chunk {index}] {chunk.chapter} > {chunk.heading}\n{'=' * 72}\n\n"
        v1_blocks.append(separator + (embed_v1 or "(empty)"))
        v2_blocks.append(separator + embed_v2)

    combined_path = EMBED_DIR / f"{stem}.embed.versions.json"
    v1_path = EMBED_DIR / f"{stem}.embed.v1.txt"
    v2_path = EMBED_DIR / f"{stem}.embed.v2.txt"

    combined_path.write_text(
        json.dumps(
            {
                "edition": edition_name,
                "source_chunks": chunks_path.relative_to(ROOT_DIR).as_posix(),
                "chunk_count": len(records),
                "chunks": records,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    v1_path.write_text("".join(v1_blocks).lstrip(), encoding="utf-8")
    v2_path.write_text("".join(v2_blocks).lstrip(), encoding="utf-8")

    return {
        "combined": combined_path,
        "v1": v1_path,
        "v2": v2_path,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Export V1/V2 embed texts from outline chunks")
    parser.add_argument(
        "chunks_path",
        nargs="?",
        default=str(CHUNKS_DIR / "제1편 민원정보공개.outline.chunks.json"),
        help="Path to *.outline.chunks.json",
    )
    parser.add_argument("--edition", default=None, help="Edition label for V2 context prefix")
    args = parser.parse_args()

    paths = export_embed_versions(Path(args.chunks_path), edition=args.edition)
    for label, path in paths.items():
        print(f"{label}: {path.relative_to(ROOT_DIR)}")


if __name__ == "__main__":
    main()
