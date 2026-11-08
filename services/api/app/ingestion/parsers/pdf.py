"""Text-based PDF parser using pypdf."""

from __future__ import annotations

import io
import re

from pypdf import PdfReader
from pypdf.errors import FileNotDecryptedError

from app.ingestion.errors import ParseError
from app.ingestion.types import ParsedBlock, ParsedDocument

_HEADING_CANDIDATE_RE = re.compile(r"^(\d+(?:\.\d+)*)\s+(\S.*)$")


def parse_pdf(*, filename: str, data: bytes) -> ParsedDocument:
    try:
        reader = PdfReader(io.BytesIO(data))
    except Exception as exc:  # noqa: BLE001
        raise ParseError(f"Failed to open PDF: {exc}") from exc

    if getattr(reader, "is_encrypted", False):
        try:
            # Empty password attempt; still reject if encrypted content remains locked.
            reader.decrypt("")
        except Exception as exc:  # noqa: BLE001
            raise ParseError("Encrypted PDFs are not supported") from exc
        if reader.is_encrypted:
            raise ParseError("Encrypted PDFs are not supported")

    blocks: list[ParsedBlock] = []
    parts: list[str] = []
    cursor = 0
    extracted_chars = 0

    try:
        pages = list(reader.pages)
    except FileNotDecryptedError as exc:
        raise ParseError("Encrypted PDFs are not supported") from exc

    for page_index, page in enumerate(pages, start=1):
        try:
            page_text = page.extract_text() or ""
        except Exception as exc:  # noqa: BLE001
            raise ParseError(f"Failed to extract text from PDF page {page_index}: {exc}") from exc

        extracted_chars += len(page_text.strip())
        for raw_line in page_text.splitlines():
            line = raw_line.strip()
            if not line:
                continue
            start = cursor
            end = cursor + len(line)
            heading_match = _HEADING_CANDIDATE_RE.match(line)
            if heading_match and len(line) < 120:
                level = heading_match.group(1).count(".") + 1
                blocks.append(
                    ParsedBlock(
                        text=line,
                        kind="heading",
                        heading_level=min(level, 6),
                        page_number=page_index,
                        start_offset=start,
                        end_offset=end,
                    )
                )
            else:
                blocks.append(
                    ParsedBlock(
                        text=line,
                        kind="paragraph",
                        page_number=page_index,
                        start_offset=start,
                        end_offset=end,
                    )
                )
            parts.append(line)
            cursor = end + 1

    if not pages:
        raise ParseError("PDF contains no pages")
    if extracted_chars < 40:
        raise ParseError(
            "PDF appears to be scanned/image-only or has insufficient extractable text; "
            "OCR is not enabled in Phase 2"
        )

    return ParsedDocument(
        filename=filename,
        kind="pdf",
        blocks=blocks,
        page_count=len(pages),
        full_text="\n".join(parts),
    )
