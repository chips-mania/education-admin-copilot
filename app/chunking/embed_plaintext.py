"""Convert chunk HTML/markdown into plain text for embedding."""

from __future__ import annotations

import html
import re

BR_TAG_RE = re.compile(r"<br\s*/?>", re.IGNORECASE)
HTML_TAG_RE = re.compile(r"<[^>]+>")
TABLE_RE = re.compile(r"<table[^>]*>.*?</table>", re.DOTALL | re.IGNORECASE)
ROW_RE = re.compile(r"<tr[^>]*>(.*?)</tr>", re.DOTALL | re.IGNORECASE)
CELL_RE = re.compile(r"<t[hd][^>]*>(.*?)</t[hd]>", re.DOTALL | re.IGNORECASE)
MARKDOWN_TABLE_SEP_RE = re.compile(r"^\|\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)+\|?\s*$")


def to_embed_plaintext(text: str) -> str:
    if not text or not text.strip():
        return ""

    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    normalized = _convert_html_tables(normalized)
    normalized = _convert_markdown_tables(normalized)
    normalized = _strip_html(normalized)
    normalized = _format_lines(normalized)
    return normalized.strip()


def _strip_html(text: str) -> str:
    text = BR_TAG_RE.sub("\n", text)
    text = HTML_TAG_RE.sub("", text)
    return html.unescape(text)


def _convert_html_tables(text: str) -> str:
    def replace_table(match: re.Match[str]) -> str:
        plain = _table_html_to_plain(match.group(0))
        return f"\n{plain}\n" if plain else ""

    return TABLE_RE.sub(replace_table, text)


def _table_html_to_plain(table_html: str) -> str:
    lines: list[str] = []
    for row_match in ROW_RE.finditer(table_html):
        cells = [
            _normalize_whitespace(_strip_html(cell))
            for cell in CELL_RE.findall(row_match.group(1))
        ]
        cells = [cell for cell in cells if cell]
        if not cells:
            continue
        if len(cells) == 1:
            lines.extend(part for part in cells[0].split("\n") if part.strip())
        else:
            lines.append(" | ".join(cells))

    return _format_section_lines(_dedupe_preserve_order(lines))


def _convert_markdown_tables(text: str) -> str:
    lines = text.split("\n")
    output: list[str] = []
    index = 0

    while index < len(lines):
        line = lines[index]
        if (
            line.strip().startswith("|")
            and index + 1 < len(lines)
            and MARKDOWN_TABLE_SEP_RE.match(lines[index + 1].strip())
        ):
            table_lines = [line]
            index += 2
            while index < len(lines) and lines[index].strip().startswith("|"):
                table_lines.append(lines[index])
                index += 1
            output.append(_markdown_table_to_plain(table_lines))
            continue

        output.append(line)
        index += 1

    return "\n".join(output)


def _markdown_table_to_plain(table_lines: list[str]) -> str:
    rows: list[list[str]] = []
    for line in table_lines:
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        rows.append(cells)

    if not rows:
        return ""

    if len(rows) == 1:
        return " | ".join(cell for cell in rows[0] if cell)

    header = rows[0]
    body = rows[1:]
    plain_rows: list[str] = []
    for row in body:
        pairs = []
        for col_index, cell in enumerate(row):
            if not cell:
                continue
            if col_index < len(header) and header[col_index]:
                pairs.append(f"{header[col_index]}: {cell}")
            else:
                pairs.append(cell)
        if pairs:
            plain_rows.append(" | ".join(pairs))

    return _format_section_lines(plain_rows)


def _format_lines(text: str) -> str:
    lines = [_normalize_whitespace(line) for line in text.split("\n")]
    formatted = [_format_label_list_line(line) if line else "" for line in lines]
    return "\n".join(line for line in formatted if line)


def _format_label_list_line(line: str) -> str:
    if ":" not in line:
        return line

    label, rest = line.split(":", 1)
    label = label.strip()
    rest = rest.strip()
    if not label or not rest:
        return line

    if _has_parenthetical_commas(rest):
        return f"{label}\n- {rest}"

    parts = [part.strip() for part in rest.split(",") if part.strip()]
    if len(parts) >= 2:
        return label + "\n" + "\n".join(f"- {part}" for part in parts)

    return line


def _format_section_lines(lines: list[str]) -> str:
    if not lines:
        return ""

    expanded: list[str] = []
    for line in lines:
        expanded.extend(part.strip() for part in line.split("\n") if part.strip())

    if len(expanded) == 1:
        return expanded[0]

    header = expanded[0]
    items = expanded[1:]
    if len(header) <= 30 and items:
        return header + "\n" + "\n".join(f"- {item}" for item in items)

    return "\n".join(expanded)


def _has_parenthetical_commas(text: str) -> bool:
    depth = 0
    for char in text:
        if char == "(":
            depth += 1
        elif char == ")":
            depth = max(depth - 1, 0)
        elif char == "," and depth > 0:
            return True
    return False


def _dedupe_preserve_order(lines: list[str]) -> list[str]:
    seen: set[str] = set()
    unique: list[str] = []
    for line in lines:
        if line not in seen:
            seen.add(line)
            unique.append(line)
    return unique


def _normalize_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()
