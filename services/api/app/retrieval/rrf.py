"""Reciprocal Rank Fusion."""

from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID


def reciprocal_rank_fusion(
    ranked_lists: Sequence[Sequence[UUID]],
    *,
    k: int = 60,
) -> list[tuple[UUID, float]]:
    """
    Fuse multiple ranked ID lists with RRF.

    score(d) = sum_i 1 / (k + rank_i(d)) where rank is 1-based.
    """
    scores: dict[UUID, float] = {}
    for ranked in ranked_lists:
        for rank, item_id in enumerate(ranked, start=1):
            scores[item_id] = scores.get(item_id, 0.0) + 1.0 / (k + rank)
    return sorted(scores.items(), key=lambda pair: pair[1], reverse=True)
