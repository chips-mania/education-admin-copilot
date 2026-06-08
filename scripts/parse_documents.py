import argparse
import json
import logging
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from app.parsers import parse_document

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)

RAW_DIR = ROOT_DIR / "data" / "raw"
PROCESSED_DIR = ROOT_DIR / "data" / "processed"
SUPPORTED_EXTENSIONS = {".hwpx", ".pdf"}


def collect_files(target: Path) -> list[Path]:
    if target.is_file():
        return [target]

    return sorted(
        path
        for path in target.rglob("*")
        if path.is_file() and path.suffix.lower() in SUPPORTED_EXTENSIONS
    )


def save_parsed_document(parsed: dict, project_root: Path) -> Path:
    output_dir = project_root / "data" / "processed" / parsed["source_type"]
    output_dir.mkdir(parents=True, exist_ok=True)

    output_path = output_dir / f"{Path(parsed['file_name']).stem}.json"
    output_path.write_text(json.dumps(parsed, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info("Saved processed JSON: %s", output_path)
    return output_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Parse HWPX/PDF documents to JSON")
    parser.add_argument(
        "target",
        nargs="?",
        default=str(RAW_DIR),
        help="File or directory path (default: data/raw)",
    )
    args = parser.parse_args()

    target = Path(args.target)
    files = collect_files(target)

    if not files:
        logger.warning("No supported documents found in: %s", target)
        return

    logger.info("Found %d document(s)", len(files))

    for file_path in files:
        parsed = parse_document(file_path, project_root=ROOT_DIR).to_dict()
        print(json.dumps(parsed, ensure_ascii=False, indent=2))
        save_parsed_document(parsed, ROOT_DIR)


if __name__ == "__main__":
    main()
