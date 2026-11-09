"""Shared ingestion data structures."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

SupportedKind = Literal["markdown", "docx", "pdf"]


@dataclass(slots=True)
class ParsedBlock:
    """A normalized content block with provenance hints."""

    text: str
    kind: Literal["heading", "paragraph", "table"]
    heading_level: int | None = None
    page_number: int | None = None
    start_offset: int = 0
    end_offset: int = 0


@dataclass(slots=True)
class ParsedDocument:
    """Parser output used by the chunker."""

    filename: str
    kind: SupportedKind
    blocks: list[ParsedBlock] = field(default_factory=list)
    page_count: int | None = None
    full_text: str = ""


@dataclass(slots=True)
class ChunkDraft:
    """Chunk ready to persist."""

    chunk_index: int
    text: str
    heading_path: str
    page_number: int | None
    start_offset: int
    end_offset: int
    token_count: int
