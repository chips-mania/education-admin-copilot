import logging
from pathlib import Path

from app.parsers.hwpx_parser import parse_hwpx
from app.parsers.pdf_parser import parse_pdf
from app.schemas.document import ParsedDocument

logger = logging.getLogger(__name__)

PARSER_BY_EXTENSION = {
    ".hwpx": parse_hwpx,
    ".pdf": parse_pdf,
}


def parse_document(file_path: Path, project_root: Path | None = None) -> ParsedDocument:
    suffix = file_path.suffix.lower()
    parser = PARSER_BY_EXTENSION.get(suffix)

    if parser is None:
        raise ValueError(f"Unsupported file extension: {suffix}")

    logger.info("Dispatching parser for extension: %s", suffix)
    return parser(file_path, project_root=project_root)
