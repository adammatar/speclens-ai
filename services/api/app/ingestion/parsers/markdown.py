"""Markdown parser preserving heading structure and offsets."""

from __future__ import annotations

import re

from app.ingestion.types import ParsedBlock, ParsedDocument

_HEADING_RE = re.compile(r"^(#{1,6})\s+(.*)$")


def parse_markdown(*, filename: str, data: bytes) -> ParsedDocument:
    text = data.decode("utf-8")
    blocks: list[ParsedBlock] = []
    cursor = 0
    paragraph_parts: list[str] = []
    paragraph_start = 0

    def flush_paragraph(end: int) -> None:
        nonlocal paragraph_parts, paragraph_start
        if not paragraph_parts:
            return
        body = "\n".join(paragraph_parts).strip()
        if body:
            blocks.append(
                ParsedBlock(
                    text=body,
                    kind="paragraph",
                    start_offset=paragraph_start,
                    end_offset=end,
                )
            )
        paragraph_parts = []

    lines = text.splitlines(keepends=True)
    for line in lines:
        line_start = cursor
        line_end = cursor + len(line)
        stripped = line.strip("\n")
        heading = _HEADING_RE.match(stripped)
        if heading:
            flush_paragraph(line_start)
            level = len(heading.group(1))
            title = heading.group(2).strip()
            blocks.append(
                ParsedBlock(
                    text=title,
                    kind="heading",
                    heading_level=level,
                    start_offset=line_start,
                    end_offset=line_end,
                )
            )
        elif stripped.strip() == "":
            flush_paragraph(line_start)
        else:
            if not paragraph_parts:
                paragraph_start = line_start
            paragraph_parts.append(stripped.rstrip())
        cursor = line_end

    flush_paragraph(len(text))
    return ParsedDocument(
        filename=filename,
        kind="markdown",
        blocks=blocks,
        page_count=None,
        full_text=text,
    )
