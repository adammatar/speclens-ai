"""Deterministic stub generator for local/CI cited QA (no external LLM)."""

from __future__ import annotations

import re
import uuid

from app.generation.base import CitationDraft, GenerationResult
from app.generation.citations import filter_citations
from app.retrieval.search import SearchHit

_INJECTION_RE = re.compile(
    r"ignore (all )?(previous|prior) instructions|system prompt|jailbreak",
    re.IGNORECASE,
)


class StubGenerator:
    """Builds a short grounded answer from top retrieved excerpts only."""

    def __init__(self, *, model_name: str) -> None:
        self._model_name = model_name

    @property
    def model_name(self) -> str:
        return self._model_name

    def generate(
        self,
        *,
        question: str,
        hits: list[SearchHit],
        allowlisted_chunk_ids: set[uuid.UUID],
        prompt_version: str,
        prior_messages: list[tuple[str, str]] | None = None,
    ) -> GenerationResult:
        _ = prior_messages  # follow-up context reserved; stub uses fresh retrieval
        usable = [hit for hit in hits if hit.chunk_id in allowlisted_chunk_ids]
        if not usable:
            return GenerationResult(
                content=(
                    "Insufficient evidence: no retrieved document excerpts support "
                    "an answer to this question."
                ),
                citations=[],
                insufficient_evidence=True,
                model=self._model_name,
                prompt_version=prompt_version,
                prompt_tokens=max(1, len(question.split())),
                completion_tokens=12,
            )

        # Document text is data: strip injection phrases from quotes used in the answer.
        cleaned_excerpts: list[str] = []
        citations: list[CitationDraft] = []
        for index, hit in enumerate(usable[:3]):
            quote = _INJECTION_RE.sub("[redacted-instruction]", hit.excerpt)
            cleaned_excerpts.append(quote)
            citations.append(
                CitationDraft(
                    chunk_id=hit.chunk_id,
                    claim_index=index,
                    source_quote=quote[:240],
                )
            )

        body = (
            f"Based on the retrieved specification excerpts, regarding "
            f'"{question.strip()}": {cleaned_excerpts[0]}'
        )
        if len(cleaned_excerpts) > 1:
            body += f" Additional support: {cleaned_excerpts[1]}"
        body += " Citations refer only to retrieved chunk IDs."

        # Attempted jailbreak citations must still be filtered.
        forged = CitationDraft(chunk_id=uuid.uuid4(), claim_index=99, source_quote="forged")
        safe_citations = filter_citations([*citations, forged], allowlisted_chunk_ids)

        return GenerationResult(
            content=body,
            citations=safe_citations,
            insufficient_evidence=False,
            model=self._model_name,
            prompt_version=prompt_version,
            prompt_tokens=max(
                1, len(question.split()) + sum(len(h.excerpt.split()) for h in usable)
            ),
            completion_tokens=max(1, len(body.split())),
        )
