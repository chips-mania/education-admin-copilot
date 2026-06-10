import argparse
import json
import logging
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from app.chunking import filter_embeddable_chunk_dicts
from app.services.embedding_service import embed_texts

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)

CHUNKS_DIR = ROOT_DIR / "data" / "processed" / "chunks"
EMBEDDINGS_DIR = ROOT_DIR / "data" / "processed" / "embeddings"


def collect_chunk_files(target: Path) -> list[Path]:
    if target.is_file():
        return [target]

    return sorted(target.rglob("*.chunks.json"))


def build_embeddings_for_file(chunks_path: Path) -> Path:
    chunks_path = chunks_path.resolve()
    payload = json.loads(chunks_path.read_text(encoding="utf-8"))
    chunks = payload.get("chunks", [])

    if not chunks:
        raise ValueError(f"No chunks found in: {chunks_path}")

    chunks = filter_embeddable_chunk_dicts(chunks)
    if not chunks:
        raise ValueError(f"No embeddable chunks remain after filtering in: {chunks_path}")

    payload["chunks"] = chunks
    texts = [chunk["content"] for chunk in chunks]
    vectors = embed_texts(texts)

    for chunk, vector in zip(chunks, vectors):
        chunk["embedding"] = vector

    relative = chunks_path.relative_to(CHUNKS_DIR.resolve())
    output_name = relative.name.replace(".chunks.json", ".embeddings.json")
    output_path = EMBEDDINGS_DIR / relative.parent / output_name
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    logger.info("Saved embeddings for %d chunk(s) to %s", len(chunks), output_path)
    return output_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Build embeddings for chunked documents")
    parser.add_argument(
        "target",
        nargs="?",
        default=str(CHUNKS_DIR),
        help="Chunks JSON file or directory (default: data/processed/chunks)",
    )
    args = parser.parse_args()

    target = Path(args.target)
    files = collect_chunk_files(target)

    if not files:
        logger.warning("No chunk files found in: %s", target)
        return

    logger.info("Found %d chunk file(s)", len(files))

    for chunks_path in files:
        output_path = build_embeddings_for_file(chunks_path)
        result = json.loads(output_path.read_text(encoding="utf-8"))
        summary = {
            "title": result.get("title"),
            "chunk_count": len(result.get("chunks", [])),
            "embedding_dim": len(result["chunks"][0]["embedding"]) if result.get("chunks") else 0,
            "output": str(output_path.relative_to(ROOT_DIR)),
        }
        print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
