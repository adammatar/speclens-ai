"""Heuristic stub extractor for CI/local (no LLM). Supports EN + HE modals."""

from __future__ import annotations

import re

from app.extraction.base import SectionInput
from app.extraction.schema import AcceptanceCriterion, RequirementDraft, SourceReference

# English modals + common Hebrew obligation / recommendation phrasing.
_MODAL = re.compile(
    r"(?P<body>.+?(?:\b(?:shall|must|should|may)\b|"
    r"חייב|חובה|נדרש|מומלץ|אסור|"
    r"יש\s+ל[\u05d0-\u05ea]+).+?)(?:\.|׃|$)",
    re.IGNORECASE | re.DOTALL,
)

_PRIORITY_EN = {
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
            if len(statement) < 8:
                continue
            lower = statement.lower()
            priority = _priority_for(statement, lower)
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
            if "roughly" in lower or "approximately" in lower or "בערך" in statement:
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


def _priority_for(statement: str, lower: str) -> str:
    for token, mapped in _PRIORITY_EN.items():
        if re.search(rf"\b{token}\b", lower):
            return mapped
    if any(tok in statement for tok in ("חייב", "חובה", "נדרש", "אסור")):
        return "must"
    if "מומלץ" in statement or "יש ל" in statement:
        return "should"
    return "unknown"


def _guess_type(section_path: str, statement: str) -> str:
    hay = f"{section_path} {statement}".lower()
    if "security" in hay or "אבטחה" in statement:
        return "security"
    if "performance" in hay or "latency" in hay or "ביצועים" in statement:
        return "performance"
    if "non-functional" in hay or "non_functional" in hay or "non functional" in hay:
        return "non_functional"
    if "interface" in hay or "ממשק" in statement:
        return "interface"
    if "constraint" in hay or "אילוץ" in statement:
        return "constraint"
    if "compliance" in hay or "תאימות" in statement:
        return "compliance"
    if (
        "functional" in hay
        or "shall" in hay
        or "must" in hay
        or any(tok in statement for tok in ("חייב", "חובה", "נדרש"))
    ):
        return "functional"
    return "unknown"
