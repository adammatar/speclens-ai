"""Extractor protocol."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Protocol

from app.extraction.schema import RequirementDraft


@dataclass(slots=True, frozen=True)
class SectionInput:
    section_path: str
    text: str
    page_number: int | None
    document_id: uuid.UUID
    document_version_id: uuid.UUID


class RequirementExtractor(Protocol):
    model_name: str
    prompt_version: str

    def extract_section(self, section: SectionInput) -> list[RequirementDraft]:
        """Extract validated requirement drafts from one section."""
