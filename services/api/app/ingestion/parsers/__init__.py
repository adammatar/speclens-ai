"""Document parsers for supported Phase 2 formats."""

from __future__ import annotations

from app.ingestion.errors import ParseError
from app.ingestion.parsers.docx import parse_docx
from app.ingestion.parsers.markdown import parse_markdown
from app.ingestion.parsers.pdf import parse_pdf
from app.ingestion.types import ParsedDocument, SupportedKind


def parse_document(*, filename: str, kind: SupportedKind, data: bytes) -> ParsedDocument:
    """Dispatch to the appropriate parser."""
    if kind == "markdown":
        return parse_markdown(filename=filename, data=data)
    if kind == "docx":
        return parse_docx(filename=filename, data=data)
    if kind == "pdf":
        return parse_pdf(filename=filename, data=data)
    raise ParseError(f"Unsupported kind: {kind}")


__all__ = ["ParseError", "parse_document"]
