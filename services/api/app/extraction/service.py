"""Requirement listing, editing, and export helpers."""

from __future__ import annotations

import csv
import io
import json
import uuid
from typing import Any

from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import (
    ExtractionJob,
    Requirement,
    RequirementPriority,
    RequirementReviewState,
    RequirementType,
)
from app.extraction.pipeline import ExtractionError
from app.extraction.schema import RequirementDraft


def get_extraction_job(session: Session, job_id: uuid.UUID) -> ExtractionJob:
    job = session.get(ExtractionJob, job_id)
    if job is None:
        raise ExtractionError(f"Extraction job not found: {job_id}")
    return job


def list_requirements(
    session: Session,
    *,
    workspace_id: uuid.UUID | None = None,
    document_id: uuid.UUID | None = None,
    document_version_id: uuid.UUID | None = None,
    review_state: str | None = None,
    requirement_type: str | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[Requirement]:
    stmt = select(Requirement).order_by(Requirement.created_at.asc())
    if workspace_id is not None:
        stmt = stmt.where(Requirement.workspace_id == workspace_id)
    if document_id is not None:
        stmt = stmt.where(Requirement.document_id == document_id)
    if document_version_id is not None:
        stmt = stmt.where(Requirement.document_version_id == document_version_id)
    if review_state is not None:
        stmt = stmt.where(Requirement.review_state == RequirementReviewState(review_state))
    if requirement_type is not None:
        stmt = stmt.where(Requirement.requirement_type == RequirementType(requirement_type))
    stmt = stmt.offset(max(0, offset)).limit(min(max(limit, 1), 500))
    return list(session.scalars(stmt).all())


def edit_requirement(
    session: Session,
    requirement_id: uuid.UUID,
    *,
    statement: str | None = None,
    rationale: str | None = None,
    requirement_type: str | None = None,
    priority: str | None = None,
    acceptance_criteria: list[dict[str, Any]] | None = None,
    dependencies: list[str] | None = None,
    ambiguities: list[str] | None = None,
    review_state: str | None = None,
) -> Requirement:
    requirement = session.get(Requirement, requirement_id)
    if requirement is None:
        raise ExtractionError(f"Requirement not found: {requirement_id}")

    # original_payload is never mutated.
    if statement is not None:
        requirement.statement = statement.strip()
    if rationale is not None:
        requirement.rationale = rationale
    if requirement_type is not None:
        requirement.requirement_type = RequirementType(requirement_type)
    if priority is not None:
        requirement.priority = RequirementPriority(priority)
    if acceptance_criteria is not None:
        requirement.acceptance_criteria = acceptance_criteria
    if dependencies is not None:
        requirement.dependencies = dependencies
    if ambiguities is not None:
        requirement.ambiguities = ambiguities

    if review_state is not None:
        new_state = RequirementReviewState(review_state)
        requirement.review_state = new_state
        if new_state == RequirementReviewState.ACCEPTED:
            requirement.is_eval_example = True
    elif (
        any(
            value is not None
            for value in (
                statement,
                rationale,
                requirement_type,
                priority,
                acceptance_criteria,
                dependencies,
                ambiguities,
            )
        )
        and requirement.review_state == RequirementReviewState.PROPOSED
    ):
        requirement.review_state = RequirementReviewState.EDITED

    # Validate resulting shape still satisfies schema (sources preserved).
    try:
        RequirementDraft.model_validate(
            {
                "external_id": requirement.external_id,
                "requirement_type": requirement.requirement_type.value,
                "statement": requirement.statement,
                "rationale": requirement.rationale,
                "priority": requirement.priority.value,
                "acceptance_criteria": requirement.acceptance_criteria,
                "dependencies": requirement.dependencies,
                "ambiguities": requirement.ambiguities,
                "contradiction_candidates": requirement.contradiction_candidates,
                "confidence": requirement.confidence,
                "sources": requirement.sources,
                "section_path": requirement.section_path,
            }
        )
    except ValidationError as exc:
        raise ExtractionError(f"Invalid requirement after edit: {exc}") from exc

    session.commit()
    session.refresh(requirement)
    return requirement


def export_requirements(
    session: Session,
    *,
    format: str,
    workspace_id: uuid.UUID | None = None,
    document_version_id: uuid.UUID | None = None,
    review_state: str | None = None,
) -> tuple[str, str]:
    rows = list_requirements(
        session,
        workspace_id=workspace_id,
        document_version_id=document_version_id,
        review_state=review_state,
        limit=500,
    )
    if format == "json":
        payload = [
            {
                "id": str(row.id),
                "document_id": str(row.document_id),
                "document_version_id": str(row.document_version_id),
                "section_path": row.section_path,
                "external_id": row.external_id,
                "requirement_type": row.requirement_type.value,
                "statement": row.statement,
                "rationale": row.rationale,
                "priority": row.priority.value,
                "acceptance_criteria": row.acceptance_criteria,
                "dependencies": row.dependencies,
                "ambiguities": row.ambiguities,
                "contradiction_candidates": row.contradiction_candidates,
                "confidence": row.confidence,
                "sources": row.sources,
                "review_state": row.review_state.value,
                "original_payload": row.original_payload,
                "is_eval_example": row.is_eval_example,
            }
            for row in rows
        ]
        return "application/json", json.dumps(payload, indent=2)

    if format == "csv":
        buffer = io.StringIO()
        writer = csv.DictWriter(
            buffer,
            fieldnames=[
                "id",
                "document_version_id",
                "section_path",
                "requirement_type",
                "priority",
                "review_state",
                "statement",
                "source_quote",
                "confidence",
                "is_eval_example",
            ],
        )
        writer.writeheader()
        for row in rows:
            quote = ""
            if row.sources:
                first = row.sources[0]
                if isinstance(first, dict):
                    quote = str(first.get("source_quote") or "")
            writer.writerow(
                {
                    "id": str(row.id),
                    "document_version_id": str(row.document_version_id),
                    "section_path": row.section_path,
                    "requirement_type": row.requirement_type.value,
                    "priority": row.priority.value,
                    "review_state": row.review_state.value,
                    "statement": row.statement,
                    "source_quote": quote,
                    "confidence": row.confidence,
                    "is_eval_example": row.is_eval_example,
                }
            )
        return "text/csv", buffer.getvalue()

    raise ExtractionError("format must be 'json' or 'csv'")
