import logging
from pathlib import Path

import fitz

from app.schemas.document import ParsedDocument, make_parsed_document

logger = logging.getLogger(__name__)


def parse_pdf(file_path: Path, project_root: Path | None = None) -> ParsedDocument:
    file_path = file_path.resolve()
    logger.info("Parsing PDF: %s", file_path)

    if not file_path.exists():
        raise FileNotFoundError(f"PDF file not found: {file_path}")

    pages: list[str] = []
    with fitz.open(file_path) as document:
        for page in document:
            text = page.get_text().strip()
            if text:
                pages.append(text)

    content = "\n\n".join(pages).strip()
    if not content:
        raise ValueError(f"No text extracted from PDF file: {file_path}")

    title = _extract_title(content, file_path.stem)
    logger.info("PDF parsed: title=%s, content_length=%d", title, len(content))

    return make_parsed_document(
        title=title,
        content=content,
        file_path=file_path,
        project_root=project_root,
    )


def _extract_title(content: str, fallback: str) -> str:
    first_line = content.splitlines()[0].strip() if content else ""
    if first_line and len(first_line) <= 100:
        return first_line
    return fallback
