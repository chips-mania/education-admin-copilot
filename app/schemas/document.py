import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from app.config.manual_toc import lookup_manual_metadata


SOURCE_TYPES = ("manual", "law", "regulation", "interpretation")

FOLDER_SOURCE_TYPE = {
    "manuals": "manual",
    "laws": "law",
    "regulations": "regulation",
    "interpretations": "interpretation",
}

SOURCE_TYPE_LABEL = {
    "manual": "업무매뉴얼",
    "law": "법령",
    "regulation": "행정규칙",
    "interpretation": "법령해석례",
}

FILENAME_CODE_PATTERN = re.compile(r"^(\d+)-(\d+)-(\d+)\s+(.+)$")


@dataclass
class ParsedDocument:
    title: str
    content: str
    source_type: str
    file_name: str
    file_path: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def infer_source_type(file_path: Path, project_root: Path | None = None) -> str:
    parts = file_path.resolve().parts
    if "raw" in parts:
        raw_index = parts.index("raw")
        if raw_index + 1 < len(parts):
            folder = parts[raw_index + 1]
            if folder in FOLDER_SOURCE_TYPE:
                return FOLDER_SOURCE_TYPE[folder]

    raise ValueError(
        f"Cannot infer source_type from path: {file_path}. "
        f"Expected data/raw/{{manuals|laws|regulations|interpretations}}/..."
    )


def to_relative_path(file_path: Path, project_root: Path | None = None) -> str:
    file_path = file_path.resolve()
    if project_root:
        try:
            return file_path.relative_to(project_root.resolve()).as_posix()
        except ValueError:
            pass
    return file_path.as_posix()


def extract_metadata_from_path(
    file_path: Path,
    title: str,
    source_type: str,
) -> dict[str, Any]:
    metadata: dict[str, Any] = {
        "title": title,
        "source": SOURCE_TYPE_LABEL.get(source_type, source_type),
    }

    match = FILENAME_CODE_PATTERN.match(file_path.stem)
    if match:
        chapter_no, section_no, item_no, name_from_file = match.groups()
        if source_type == "manual":
            metadata.update(
                lookup_manual_metadata(
                    int(chapter_no),
                    int(section_no),
                    int(item_no),
                    title or name_from_file.strip(),
                )
            )
        else:
            metadata["chapter"] = f"제{int(chapter_no)}편"
            metadata["section"] = f"제{int(section_no)}장"
            metadata["item"] = f"제{int(item_no)}절"
            metadata["title"] = title or name_from_file.strip()

    parent = file_path.parent.name
    if parent not in FOLDER_SOURCE_TYPE and parent not in {"raw", "manuals", "laws", "regulations", "interpretations"}:
        metadata["folder"] = parent

    return metadata


def make_parsed_document(
    title: str,
    content: str,
    file_path: Path,
    project_root: Path | None = None,
    metadata: dict[str, Any] | None = None,
) -> ParsedDocument:
    source_type = infer_source_type(file_path, project_root)
    doc_metadata = metadata or extract_metadata_from_path(file_path, title, source_type)
    doc_metadata.setdefault("title", title)

    return ParsedDocument(
        title=title,
        content=content,
        source_type=source_type,
        file_name=file_path.name,
        file_path=to_relative_path(file_path, project_root),
        metadata=doc_metadata,
    )
