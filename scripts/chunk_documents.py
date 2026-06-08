import argparse
import json
import logging
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from app.chunking import chunk_document

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)

PROCESSED_DIR = ROOT_DIR / "data" / "processed"
CHUNKS_DIR = PROCESSED_DIR / "chunks"


def collect_parsed_files(target: Path) -> list[Path]:
    if target.is_file():
        return [target]

    return sorted(target.rglob("*.json"))


def chunk_parsed_file(parsed_path: Path) -> Path:
    parsed = json.loads(parsed_path.read_text(encoding="utf-8"))
    chunks = chunk_document(parsed["content"], metadata=parsed.get("metadata", {}))

    relative = parsed_path.relative_to(PROCESSED_DIR)
    output_path = CHUNKS_DIR / relative.with_suffix(".chunks.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    payload = {
        "title": parsed.get("title"),
        "source_type": parsed.get("source_type"),
        "file_name": parsed.get("file_name"),
        "file_path": parsed.get("file_path"),
        "chunks": [chunk.to_dict() for chunk in chunks],
    }
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info("Saved %d chunk(s) to %s", len(chunks), output_path)
    return output_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Chunk parsed JSON documents")
    parser.add_argument(
        "target",
        nargs="?",
        default=str(PROCESSED_DIR),
        help="Parsed JSON file or directory (default: data/processed)",
    )
    args = parser.parse_args()

    target = Path(args.target)
    files = [
        path
        for path in collect_parsed_files(target)
        if "chunks" not in path.parts and path.suffix == ".json"
    ]

    if not files:
        logger.warning("No parsed JSON files found in: %s", target)
        return

    logger.info("Found %d parsed file(s)", len(files))

    for parsed_path in files:
        output_path = chunk_parsed_file(parsed_path)
        result = json.loads(output_path.read_text(encoding="utf-8"))
        print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
