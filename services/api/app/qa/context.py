"""Assemble retrieval context under a token budget."""

from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.retrieval.search import SearchHit, search_chunks


def estimate_tokens(text: str) -> int:
    words = [part for part in text.split() if part]
    return max(1, len(words)) if text.strip() else 0


def assemble_context(
    session: Session,
    *,
    question: str,
    workspace_id: uuid.UUID,
    document_ids: list[uuid.UUID] | None = None,
    document_version_ids: list[uuid.UUID] | None = None,
    settings: Settings | None = None,
) -> list[SearchHit]:
    """Retrieve and pack chunks for QA without exceeding the context budget."""
    cfg = settings or get_settings()
    hits = search_chunks(
        session,
        query=question,
        workspace_id=workspace_id,
        document_ids=document_ids,
        document_version_ids=document_version_ids,
        limit=cfg.qa_max_context_chunks,
        settings=cfg,
    )
    packed: list[SearchHit] = []
    used = 0
    budget = cfg.qa_context_token_budget
    for hit in hits:
        if hit.rrf_score < cfg.qa_min_rrf_score:
            continue
        cost = estimate_tokens(hit.excerpt) + estimate_tokens(hit.heading_path)
        if packed and used + cost > budget:
            break
        packed.append(hit)
        used += cost
    return packed


def evidence_is_sufficient(hits: list[SearchHit], settings: Settings | None = None) -> bool:
    cfg = settings or get_settings()
    if not hits:
        return False
    return max(hit.rrf_score for hit in hits) >= cfg.qa_min_rrf_score
