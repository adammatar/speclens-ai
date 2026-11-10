"""Citation fail-closed policy for cited QA turns."""

from __future__ import annotations

from app.db.models import MessageStatus


def resolve_answer_status(
    *,
    generator_insufficient_evidence: bool,
    safe_citation_count: int,
) -> MessageStatus:
    """Decide assistant message status after citation allow-list filtering.

    Completed answers require at least one citation whose chunk_id was retrieved.
    Abstention or zero surviving citations → insufficient_evidence (never completed).
    """
    if generator_insufficient_evidence or safe_citation_count <= 0:
        return MessageStatus.INSUFFICIENT_EVIDENCE
    return MessageStatus.COMPLETED
