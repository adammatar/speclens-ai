"""Heuristic stub extractor for CI/local (no LLM)."""

from __future__ import annotations

import re

from app.extraction.base import SectionInput
from app.extraction.schema import AcceptanceCriterion, RequirementDraft, SourceReference

_MODAL = re.compile(
    r"\b(?P<body>.+?\b(?:shall|must|should|may)\b.+?)(?:\.|$)",
    re.IGNORECASE | re.DOTALL,
)
_PRIORITY = {
    "shall": "must",
    "must": "must",
    "should": "should",
    "may": "could",
}


class StubRequirementExtractor:
    model_name = "speclens-stub-extract-v1"
    prompt_version = "extraction-v1"

    def extract_section(self, section: SectionInput) -> list[RequirementDraft]:
        drafts: list[RequirementDraft] = []
        for match in _MODAL.finditer(section.text):
            statement = " ".join(match.group("body").split()).strip()
            if len(statement) < 12:
                continue
            lower = statement.lower()
            priority = "unknown"
            for token, mapped in _PRIORITY.items():
                if re.search(rf"\b{token}\b", lower):
                    priority = mapped
                    break
            req_type = _guess_type(section.section_path, statement)
            quote = statement[:500]
            source = SourceReference(
                document_id=section.document_id,
                document_version_id=section.document_version_id,
                section_path=section.section_path or None,
                page_number=section.page_number,
                source_quote=quote,
            )
            ambiguities: list[str] = []
            if "roughly" in lower or "approximately" in lower:
                ambiguities.append("Contains approximate language")
            drafts.append(
                RequirementDraft(
                    external_id=None,
                    requirement_type=req_type,  # type: ignore[arg-type]
                    statement=statement,
                    rationale=None,
                    priority=priority,  # type: ignore[arg-type]
                    acceptance_criteria=[
                        AcceptanceCriterion(
                            statement=f"Verify: {statement}",
                            source=source,
                        )
                    ],
                    dependencies=[],
                    ambiguities=ambiguities,
                    contradiction_candidates=[],
                    confidence=0.55,
                    sources=[source],
                    section_path=section.section_path,
                )
            )
        return drafts


def _guess_type(section_path: str, statement: str) -> str:
    hay = f"{section_path} {statement}".lower()
    if "security" in hay:
        return "security"
    if "performance" in hay or "latency" in hay:
        return "performance"
    if "non-functional" in hay or "non_functional" in hay or "non functional" in hay:
        return "non_functional"
    if "interface" in hay:
        return "interface"
    if "constraint" in hay:
        return "constraint"
    if "compliance" in hay:
        return "compliance"
    if "functional" in hay or "shall" in hay or "must" in hay:
        return "functional"
    return "unknown"
