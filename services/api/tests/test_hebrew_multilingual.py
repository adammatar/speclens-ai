"""Hebrew / multilingual smoke tests for stub embed, extract, and align."""

from __future__ import annotations

import uuid
from types import SimpleNamespace

from app.compare.align import align_requirements, normalize_statement, statement_similarity
from app.db.models import RequirementPriority
from app.embeddings.stub import StubEmbedder
from app.extraction.base import SectionInput
from app.extraction.stub import StubRequirementExtractor


def test_stub_embedder_handles_hebrew_tokens() -> None:
    embedder = StubEmbedder(model_name="speclens-stub-v1", dims=64)
    he = embedder.embed_texts(["ג׳ון נולד במרץ אלפיים"])[0]
    en = embedder.embed_texts(["alpha bravo"])[0]
    he2 = embedder.embed_texts(["ג׳ון נולד במרץ אלפיים"])[0]
    assert he == he2
    assert he != en
    assert abs(sum(v * v for v in he) - 1.0) < 1e-6


def test_stub_extractor_finds_hebrew_modals() -> None:
    extractor = StubRequirementExtractor()
    section = SectionInput(
        document_id=uuid.uuid4(),
        document_version_id=uuid.uuid4(),
        section_path="אבטחה",
        page_number=1,
        text="המערכת חייבת לאמת משתמש לפני גישה. אסור לשמור מפתחות בלוגים.",
    )
    drafts = extractor.extract_section(section)
    assert len(drafts) >= 1
    joined = " ".join(d.statement for d in drafts)
    assert "חייבת" in joined or "אסור" in joined


def test_align_similarity_works_for_hebrew() -> None:
    a = "המערכת חייבת להגביל ל־120 בקשות לדקה"
    b = "המערכת חייבת להגביל ל־60 בקשות לדקה"
    assert statement_similarity(a, b) > 0.5
    assert normalize_statement(a)


def _req(statement: str) -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid.uuid4(),
        external_id=None,
        statement=statement,
        priority=RequirementPriority.MUST,
        acceptance_criteria=[],
        sources=[{"source_quote": statement}],
    )


def test_align_detects_hebrew_change() -> None:
    base = [_req("המערכת חייבת להגביל ל־120 בקשות לדקה")]
    target = [_req("המערכת חייבת להגביל ל־60 בקשות לדקה")]
    pairs = align_requirements(base, target)  # type: ignore[arg-type]
    assert pairs
    matched = [p for p in pairs if p.base is not None and p.target is not None]
    assert matched
    assert matched[0].similarity > 0.5
