"""Mandatory requirement schema validation tests."""

from __future__ import annotations

import uuid

import pytest
from pydantic import ValidationError

from app.extraction.base import SectionInput
from app.extraction.schema import RequirementDraft, SourceReference
from app.extraction.stub import StubRequirementExtractor


def test_requirement_requires_source_quote() -> None:
    with pytest.raises(ValidationError):
        RequirementDraft(
            statement="The system shall encrypt data at rest.",
            sources=[],
        )


def test_requirement_rejects_blank_source_quote() -> None:
    with pytest.raises(ValidationError):
        SourceReference(
            document_id=uuid.uuid4(),
            document_version_id=uuid.uuid4(),
            source_quote="   ",
        )


def test_stub_extractor_emits_quoted_requirements() -> None:
    doc_id = uuid.uuid4()
    ver_id = uuid.uuid4()
    section = SectionInput(
        section_path="Requirements / Functional",
        text=(
            "The system shall accept Markdown uploads and preserve heading paths.\n"
            "Processing shall not block the API request thread."
        ),
        page_number=1,
        document_id=doc_id,
        document_version_id=ver_id,
    )
    drafts = StubRequirementExtractor().extract_section(section)
    assert len(drafts) >= 2
    for draft in drafts:
        assert draft.sources
        assert all(s.source_quote.strip() for s in draft.sources)
        RequirementDraft.model_validate(draft.model_dump())
