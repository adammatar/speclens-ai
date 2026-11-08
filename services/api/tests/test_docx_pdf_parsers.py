"""Parser tests for DOCX and PDF using synthetic in-memory fixtures."""

from __future__ import annotations

import io

import pytest
from docx import Document
from pypdf import PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject, NumberObject

from app.ingestion.errors import ParseError
from app.ingestion.parsers.docx import parse_docx
from app.ingestion.parsers.pdf import parse_pdf


def _make_docx_bytes() -> bytes:
    document = Document()
    document.add_heading("Title", level=1)
    document.add_heading("Section", level=2)
    document.add_paragraph("Hello from a synthetic DOCX fixture for SpecLens tests.")
    buffer = io.BytesIO()
    document.save(buffer)
    return buffer.getvalue()


def _make_text_pdf_bytes(text: str) -> bytes:
    # Minimal PDF with a content stream containing visible text operators.
    writer = PdfWriter()
    page = writer.add_blank_page(width=612, height=792)
    content = DecodedStreamObject()
    # Simple text object; enough for pypdf extract_text on many builds.
    content.set_data(f"BT /F1 12 Tf 72 720 Td ({text}) Tj ET".encode("latin-1", errors="ignore"))
    page[NameObject("/Contents")] = content
    resources = DictionaryObject()
    font = DictionaryObject()
    font[NameObject("/Type")] = NameObject("/Font")
    font[NameObject("/Subtype")] = NameObject("/Type1")
    font[NameObject("/BaseFont")] = NameObject("/Helvetica")
    fonts = DictionaryObject()
    fonts[NameObject("/F1")] = font
    resources[NameObject("/Font")] = fonts
    page[NameObject("/Resources")] = resources
    page[NameObject("/MediaBox")] = writer.pages[0].mediabox
    _ = NumberObject  # kept for clarity / future box tweaks
    out = io.BytesIO()
    writer.write(out)
    return out.getvalue()


def test_parse_docx_extracts_headings_and_paragraphs() -> None:
    parsed = parse_docx(filename="sample.docx", data=_make_docx_bytes())
    assert parsed.kind == "docx"
    assert any(block.kind == "heading" for block in parsed.blocks)
    assert any("synthetic DOCX" in block.text for block in parsed.blocks)


def test_parse_pdf_rejects_insufficient_text() -> None:
    writer = PdfWriter()
    writer.add_blank_page(width=200, height=200)
    out = io.BytesIO()
    writer.write(out)
    with pytest.raises(ParseError, match="scanned/image-only|insufficient"):
        parse_pdf(filename="blank.pdf", data=out.getvalue())
