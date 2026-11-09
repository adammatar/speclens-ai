"""Alignment unit tests - minor wording must not become entirely new."""

from __future__ import annotations

import uuid
from types import SimpleNamespace

from app.compare.align import align_requirements, statement_similarity
from app.db.models import ChangeCategory, RequirementPriority


def _req(
    statement: str,
    *,
    external_id: str | None = None,
    priority: RequirementPriority = RequirementPriority.MUST,
) -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid.uuid4(),
        external_id=external_id,
        statement=statement,
        priority=priority,
        acceptance_criteria=[],
        sources=[{"source_quote": statement}],
    )


def test_minor_wording_change_aligns_not_added_removed() -> None:
    base = [
        _req("The system shall accept Markdown uploads and preserve heading paths."),
        _req("The system shall reject unsupported file types with a clear validation error."),
    ]
    target = [
        _req("The system shall accept Markdown uploads and preserve heading paths on chunks."),
        _req("The system shall reject unsupported file types with a clear validation error."),
    ]
    # Cast to Requirement-like for align_requirements typing via duck typing.
    pairs = align_requirements(base, target)  # type: ignore[arg-type]
    categories = {pair.category for pair in pairs}
    assert ChangeCategory.ADDED not in categories
    assert ChangeCategory.REMOVED not in categories
    assert any(
        pair.category
        in {
            ChangeCategory.CLARIFIED,
            ChangeCategory.BEHAVIOR_CHANGED,
        }
        for pair in pairs
        if pair.base is not None and pair.target is not None
    )
    matched = [p for p in pairs if p.base is not None and p.target is not None]
    assert len(matched) == 2
    assert all(p.similarity >= 0.72 for p in matched)


def test_external_id_match_preferred() -> None:
    base = [_req("Old wording shall remain.", external_id="REQ-1")]
    target = [_req("Completely different shall text for REQ-1.", external_id="REQ-1")]
    pairs = align_requirements(base, target)  # type: ignore[arg-type]
    assert len(pairs) == 1
    assert pairs[0].base is not None and pairs[0].target is not None
    assert pairs[0].base.external_id == "REQ-1"


def test_statement_similarity_high_for_paraphrase() -> None:
    a = "The system shall detect duplicate uploads using a SHA-256 content digest."
    b = "The system shall detect duplicate uploads via a SHA-256 content digest."
    assert statement_similarity(a, b) >= 0.72


def test_priority_change_detected() -> None:
    base = [
        _req(
            "Processing shall not block the API request thread.",
            priority=RequirementPriority.MUST,
        )
    ]
    target = [
        _req(
            "Processing shall not block the API request thread.",
            priority=RequirementPriority.SHOULD,
        )
    ]
    pairs = align_requirements(base, target)  # type: ignore[arg-type]
    assert pairs[0].category == ChangeCategory.PRIORITY_CHANGED
