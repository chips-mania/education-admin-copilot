import argparse
import json
import logging
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from app.db.repositories import DocumentRepository

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)

EMBEDDINGS_DIR = ROOT_DIR / "data" / "processed" / "embeddings"


def collect_embedding_files(target: Path) -> list[Path]:
    if target.is_file():
        return [target]

    return sorted(target.rglob("*.embeddings.json"))


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest embeddings JSON into Supabase")
    parser.add_argument(
        "target",
        nargs="?",
        default=str(EMBEDDINGS_DIR),
        help="Embeddings JSON file or directory (default: data/processed/embeddings)",
    )
    args = parser.parse_args()

    target = Path(args.target)
    files = collect_embedding_files(target)

    if not files:
        logger.warning("No embeddings files found in: %s", target)
        return

    repository = DocumentRepository()
    results = []

    for embedding_path in files:
        payload = json.loads(embedding_path.read_text(encoding="utf-8"))
        result = repository.ingest_embedding_document(payload)
        result["file_path"] = payload["file_path"]
        results.append(result)
        logger.info("Ingested %s -> document_id=%s", payload["file_path"], result["document_id"])

    print(json.dumps(results, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
