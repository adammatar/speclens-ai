"""DOCX parser using python-docx."""

from __future__ import annotations

import io
import re

from docx import Document

from app.ingestion.errors import ParseError
from app.ingestion.types import ParsedBlock, ParsedDocument

_HEADING_STYLE_RE = re.compile(r"^Heading\s+(\d+)$", re.IGNORECASE)


def parse_docx(*, filename: str, data: bytes) -> ParsedDocument:
    try:
        document = Document(io.BytesIO(data))
    except Exception as exc:  # noqa: BLE001
        raise ParseError(f"Failed to open DOCX: {exc}") from exc

    blocks: list[ParsedBlock] = []
    cursor = 0
    parts: list[str] = []

    for paragraph in document.paragraphs:
        text = paragraph.text.strip()
        if not text:
            continue
        style_name = paragraph.style.name if paragraph.style is not None else ""
        match = _HEADING_STYLE_RE.match(style_name or "")
        start = cursor
        end = cursor + len(text)
        if match:
            blocks.append(
                ParsedBlock(
                    text=text,
                    kind="heading",
                    heading_level=int(match.group(1)),
                    start_offset=start,
                    end_offset=end,
                )
            )
        else:
            blocks.append(
                ParsedBlock(
                    text=text,
                    kind="paragraph",
                    start_offset=start,
                    end_offset=end,
                )
            )
        parts.append(text)
        cursor = end + 2  # account for paragraph break in reconstructed text

    # Tables as flattened text blocks (Phase 2 provenance stub).
    for table in document.tables:
        rows: list[str] = []
        for row in table.rows:
            cells = [cell.text.strip() for cell in row.cells]
            rows.append(" | ".join(cell for cell in cells if cell))
        table_text = "\n".join(row for row in rows if row).strip()
        if not table_text:
            continue
        start = cursor
        end = cursor + len(table_text)
        blocks.append(
            ParsedBlock(
                text=table_text,
                kind="table",
                start_offset=start,
                end_offset=end,
            )
        )
        parts.append(table_text)
        cursor = end + 2

    full_text = "\n\n".join(parts)
    return ParsedDocument(
        filename=filename,
        kind="docx",
        blocks=blocks,
        page_count=None,
        full_text=full_text,
    )
