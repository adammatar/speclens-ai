"""Pydantic requirement schema (mandatory validation)."""

from __future__ import annotations

import uuid
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator


class SourceReference(BaseModel):
    document_id: uuid.UUID
    document_version_id: uuid.UUID
    section_path: str | None = None
    page_number: int | None = None
    source_quote: str = Field(min_length=1)

    @field_validator("source_quote")
    @classmethod
    def quote_must_be_nonblank(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("source_quote must be non-empty")
        return cleaned


class AcceptanceCriterion(BaseModel):
    statement: str = Field(min_length=1)
    source: SourceReference | None = None


class RequirementDraft(BaseModel):
    """Validated extraction output before persistence."""

    external_id: str | None = None
    requirement_type: Literal[
        "functional",
        "non_functional",
        "constraint",
        "interface",
        "security",
        "performance",
        "compliance",
        "unknown",
    ] = "unknown"
    statement: str = Field(min_length=1)
    rationale: str | None = None
    priority: Literal["must", "should", "could", "unknown"] = "unknown"
    acceptance_criteria: list[AcceptanceCriterion] = Field(default_factory=list)
    dependencies: list[str] = Field(default_factory=list)
    ambiguities: list[str] = Field(default_factory=list)
    contradiction_candidates: list[str] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0, default=0.5)
    sources: list[SourceReference] = Field(min_length=1)
    section_path: str = ""

    @model_validator(mode="after")
    def require_source_quote(self) -> RequirementDraft:
        if not self.sources:
            raise ValueError("every requirement must include at least one source")
        if not any(source.source_quote.strip() for source in self.sources):
            raise ValueError("every requirement must contain a source quote")
        return self
