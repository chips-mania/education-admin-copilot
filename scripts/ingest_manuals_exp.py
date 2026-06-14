"""Clear Supabase and ingest manuals_exp with outline chunking + dual V1/V2 embeddings."""

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

from app.chunking import (  # noqa: E402
    MAX_EMBEDDABLE_TOKENS,
    chunk_hwpx_outline,
    filter_embeddable_chunk_dicts,
    outline_chunks_to_ingest_dicts,
)
from app.db.repositories import DocumentRepository
from app.schemas.document import extract_metadata_from_path, infer_source_type, to_relative_path
from app.services.embedding_service import attach_dual_embeddings

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)

MANUALS_EXP_DIR = ROOT_DIR / "data" / "raw" / "manuals_exp"
CHUNKS_DIR = ROOT_DIR / "data" / "processed" / "chunks" / "manuals_exp"
EMBEDDINGS_DIR = ROOT_DIR / "data" / "processed" / "embeddings" / "manuals_exp"


def collect_hwpx_files(target: Path) -> list[Path]:
    if target.is_file():
        return [target]
    return sorted(target.glob("*.hwpx"))


def ingest_hwpx_file(
    file_path: Path,
    repository: DocumentRepository,
    *,
    save_artifacts: bool = True,
) -> dict:
    file_path = file_path.resolve()
    edition = file_path.stem
    source_type = infer_source_type(file_path, ROOT_DIR)
    metadata = extract_metadata_from_path(file_path, edition, source_type)
    metadata["edition"] = edition

    outline_chunks = chunk_hwpx_outline(file_path, metadata=metadata, edition=edition)
    if not outline_chunks:
        raise ValueError(f"No outline chunks produced for: {file_path}")

    chunk_dicts = outline_chunks_to_ingest_dicts(
        outline_chunks,
        edition=edition,
    )
    chunk_dicts = filter_embeddable_chunk_dicts(chunk_dicts)
    if not chunk_dicts:
        raise ValueError(
            f"No embeddable chunks remain for {file_path.name} (>{MAX_EMBEDDABLE_TOKENS} tokens)"
        )

    attach_dual_embeddings(chunk_dicts)

    relative_path = to_relative_path(file_path, ROOT_DIR)
    payload = {
        "title": edition,
        "source_type": source_type,
        "file_name": file_path.name,
        "file_path": relative_path,
        "chunks": chunk_dicts,
    }

    if save_artifacts:
        chunks_path = CHUNKS_DIR / f"{file_path.stem}.outline.chunks.json"
        embeddings_path = EMBEDDINGS_DIR / f"{file_path.stem}.embeddings.json"
        chunks_path.parent.mkdir(parents=True, exist_ok=True)
        embeddings_path.parent.mkdir(parents=True, exist_ok=True)
        chunks_path.write_text(
            json.dumps(
                {
                    "title": edition,
                    "source_type": source_type,
                    "file_name": file_path.name,
                    "file_path": relative_path,
                    "edition": edition,
                    "chunks": [
                        {
                            "chunk_no": c["chunk_no"],
                            "chapter": c["chapter"],
                            "heading": c["heading"],
                            "content": c["content"],
                            "table": c["metadata"].get("table"),
                        }
                        for c in chunk_dicts
                    ],
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        embeddings_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    result = repository.ingest_embedding_document(payload, replace=True)
    return {
        "file_name": file_path.name,
        "file_path": relative_path,
        "document_id": result["document_id"],
        "chunk_count": result["stored_chunks"],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest manuals_exp into Supabase")
    parser.add_argument(
        "target",
        nargs="?",
        default=str(MANUALS_EXP_DIR),
        help="HWPX file or directory (default: data/raw/manuals_exp)",
    )
    parser.add_argument(
        "--skip-clear",
        action="store_true",
        help="Do not delete existing Supabase documents before ingest",
    )
    parser.add_argument(
        "--no-artifacts",
        action="store_true",
        help="Skip writing local chunks/embeddings JSON artifacts",
    )
    args = parser.parse_args()

    files = collect_hwpx_files(Path(args.target))
    if not files:
        logger.error("No HWPX files found in: %s", args.target)
        sys.exit(1)

    repository = DocumentRepository()

    if not args.skip_clear:
        deleted = repository.delete_all_documents()
        logger.info("Cleared Supabase documents: %d", deleted)

    results = []
    for file_path in files:
        logger.info("Ingesting %s", file_path.name)
        try:
            result = ingest_hwpx_file(
                file_path,
                repository,
                save_artifacts=not args.no_artifacts,
            )
            results.append(result)
            logger.info(
                "OK %s -> document_id=%s chunks=%s",
                result["file_name"],
                result["document_id"],
                result["chunk_count"],
            )
        except Exception as exc:
            logger.exception("Failed to ingest %s: %s", file_path.name, exc)
            results.append({"file_name": file_path.name, "error": str(exc)})

    summary = {
        "files_total": len(files),
        "files_ok": sum(1 for item in results if "error" not in item),
        "files_failed": sum(1 for item in results if "error" in item),
        "total_chunks": sum(item.get("chunk_count", 0) for item in results),
        "results": results,
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
