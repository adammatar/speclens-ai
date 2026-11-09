"""Generation result types and protocol."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Protocol

from app.retrieval.search import SearchHit


@dataclass(slots=True)
class CitationDraft:
    chunk_id: uuid.UUID
    claim_index: int = 0
    source_quote: str | None = None


@dataclass(slots=True)
class GenerationResult:
    content: str
    citations: list[CitationDraft] = field(default_factory=list)
    insufficient_evidence: bool = False
    model: str = ""
    prompt_version: str = ""
    prompt_tokens: int = 0
    completion_tokens: int = 0


class Generator(Protocol):
    @property
    def model_name(self) -> str: ...

    def generate(
        self,
        *,
        question: str,
        hits: list[SearchHit],
        allowlisted_chunk_ids: set[uuid.UUID],
        prompt_version: str,
        prior_messages: list[tuple[str, str]] | None = None,
    ) -> GenerationResult: ...
