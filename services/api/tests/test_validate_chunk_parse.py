"""Unit tests for validation, markdown parsing, and chunking."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.ingestion.chunking import chunk_document, estimate_tokens
from app.ingestion.hashing import sha256_hex
from app.ingestion.parsers.markdown import parse_markdown
from app.ingestion.validate import UploadValidationError, validate_upload

FIXTURES = Path(__file__).parent / "fixtures"


def test_validate_upload_accepts_markdown() -> None:
    result = validate_upload(
        filename="spec.md",
        content_type="text/markdown",
        size=128,
    )
    assert result.kind == "markdown"


def test_validate_upload_rejects_bad_extension() -> None:
    with pytest.raises(UploadValidationError):
        validate_upload(filename="x.exe", content_type="application/octet-stream", size=10)


def test_sha256_stable() -> None:
    assert sha256_hex(b"abc") == sha256_hex(b"abc")
    assert sha256_hex(b"abc") != sha256_hex(b"abcd")


def test_parse_and_chunk_markdown_preserves_heading_paths() -> None:
    data = (FIXTURES / "sample.md").read_bytes()
    parsed = parse_markdown(filename="sample.md", data=data)
    assert any(block.kind == "heading" for block in parsed.blocks)
    drafts = chunk_document(parsed)
    assert drafts
    assert all(draft.end_offset >= draft.start_offset for draft in drafts)
    # Section-aware: requirement chunks should include a heading path.
    headed = [draft for draft in drafts if draft.heading_path]
    assert headed
    assert any("Requirements" in draft.heading_path for draft in headed)


def test_chunker_does_not_merge_unrelated_sections() -> None:
    # Build a synthetic parsed doc with two sections and oversized bodies.
    from app.ingestion.types import ParsedBlock, ParsedDocument

    body_a = " ".join(["alpha"] * 500)
    body_b = " ".join(["bravo"] * 500)
    parsed = ParsedDocument(
        filename="x.md",
        kind="markdown",
        blocks=[
            ParsedBlock(text="A", kind="heading", heading_level=1, start_offset=0, end_offset=1),
            ParsedBlock(
                text=body_a,
                kind="paragraph",
                start_offset=2,
                end_offset=2 + len(body_a),
            ),
            ParsedBlock(
                text="B",
                kind="heading",
                heading_level=1,
                start_offset=10000,
                end_offset=10001,
            ),
            ParsedBlock(
                text=body_b,
                kind="paragraph",
                start_offset=10002,
                end_offset=10002 + len(body_b),
            ),
        ],
        full_text="",
    )
    drafts = chunk_document(parsed, max_tokens=200, overlap_tokens=20)
    assert drafts
    assert all(("alpha" in d.text) ^ ("bravo" in d.text) for d in drafts)
    assert estimate_tokens(body_a) > 200
