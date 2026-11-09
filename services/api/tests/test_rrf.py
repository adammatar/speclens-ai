"""Unit tests for Reciprocal Rank Fusion."""

from __future__ import annotations

import uuid

from app.retrieval.rrf import reciprocal_rank_fusion


def test_rrf_prefers_items_high_in_multiple_lists() -> None:
    a, b, c = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    fused = reciprocal_rank_fusion([[a, b, c], [a, c, b]], k=60)
    assert fused[0][0] == a
    assert fused[0][1] > fused[1][1]


def test_rrf_handles_disjoint_lists() -> None:
    a, b = uuid.uuid4(), uuid.uuid4()
    fused = reciprocal_rank_fusion([[a], [b]], k=60)
    ids = {item for item, _ in fused}
    assert ids == {a, b}
