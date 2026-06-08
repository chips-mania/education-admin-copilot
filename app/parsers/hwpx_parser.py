import logging
import re
from pathlib import Path

from hwpx import HwpxDocument

from app.schemas.document import ParsedDocument, make_parsed_document

logger = logging.getLogger(__name__)


def parse_hwpx(file_path: Path, project_root: Path | None = None) -> ParsedDocument:
    file_path = file_path.resolve()
    logger.info("Parsing HWPX: %s", file_path)

    if not file_path.exists():
        raise FileNotFoundError(f"HWPX file not found: {file_path}")

    with HwpxDocument.open(str(file_path)) as document:
        content = _normalize_content(document.export_rich_markdown())

    if not content:
        raise ValueError(f"No text extracted from HWPX file: {file_path}")

    title = _extract_title(content, file_path.stem)
    logger.info("HWPX parsed: title=%s, content_length=%d", title, len(content))

    return make_parsed_document(
        title=title,
        content=content,
        file_path=file_path,
        project_root=project_root,
    )


def _normalize_content(content: str) -> str:
    lines = []
    for line in content.splitlines():
        cleaned = re.sub(r"\*\*", "", line).rstrip()
        if cleaned.strip() == "" and (not lines or lines[-1] == ""):
            continue
        lines.append(cleaned)
    return "\n".join(lines).strip()


def _extract_title(content: str, fallback: str) -> str:
    for line in content.splitlines():
        stripped = re.sub(r"\*\*", "", line).strip()
        if not stripped:
            continue
        if stripped.startswith("|") and stripped.endswith("|"):
            cells = [cell.strip() for cell in stripped.strip("|").split("|") if cell.strip()]
            if cells:
                return cells[0]
        if len(stripped) <= 100:
            return stripped

    match = re.match(r"^\d+-\d+-\d+\s+(.+)$", fallback)
    if match:
        return match.group(1).strip()
    return fallback
