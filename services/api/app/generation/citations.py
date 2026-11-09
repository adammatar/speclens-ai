"""Citation allow-list enforcement."""

from __future__ import annotations

import uuid

from app.generation.base import CitationDraft


def filter_citations(
    drafts: list[CitationDraft],
    allowlisted_chunk_ids: set[uuid.UUID],
) -> list[CitationDraft]:
    """Drop any citation whose chunk_id was not retrieved."""
    return [draft for draft in drafts if draft.chunk_id in allowlisted_chunk_ids]
