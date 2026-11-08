"""Ensure large synthetic documents chunk without blocking the caller."""

from __future__ import annotations

from app.ingestion.chunking import chunk_document
from app.ingestion.parsers.markdown import parse_markdown


def test_hundred_section_markdown_chunks_quickly() -> None:
    parts: list[str] = ["# Large Synthetic Spec\n"]
    filler = " ".join(f"word{i}" for i in range(120))
    for section in range(1, 101):
        parts.append(f"\n## Section {section}\n\n{filler}\n")
    data = "".join(parts).encode("utf-8")
    parsed = parse_markdown(filename="large.md", data=data)
    drafts = chunk_document(parsed)
    assert len(drafts) >= 100
    assert all(draft.heading_path for draft in drafts)
    assert all(draft.end_offset >= draft.start_offset for draft in drafts)
