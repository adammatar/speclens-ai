"""Comparison job orchestration."""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.compare.align import align_requirements, source_quote
from app.db.models import (
    ChangeDecision,
    ComparisonJob,
    ComparisonJobStatus,
    DocumentVersion,
    Requirement,
    RequirementChange,
)

logger = logging.getLogger(__name__)


class CompareError(ValueError):
    """Raised for invalid comparison requests."""


def create_comparison_job(
    session: Session,
    *,
    base_document_version_id: uuid.UUID,
    target_document_version_id: uuid.UUID,
) -> ComparisonJob:
    if base_document_version_id == target_document_version_id:
        raise CompareError("base and target document versions must differ")
    base = session.get(DocumentVersion, base_document_version_id)
    target = session.get(DocumentVersion, target_document_version_id)
    if base is None or target is None:
        raise CompareError("base or target document version not found")
    if base.workspace_id != target.workspace_id:
        raise CompareError("versions must belong to the same workspace")

    base_reqs = _load_requirements(session, base_document_version_id)
    target_reqs = _load_requirements(session, target_document_version_id)
    if not base_reqs and not target_reqs:
        raise CompareError("both versions lack extracted requirements; run extraction first")

    job = ComparisonJob(
        workspace_id=base.workspace_id,
        base_document_version_id=base.id,
        target_document_version_id=target.id,
        status=ComparisonJobStatus.QUEUED,
        progress_pct=0,
        change_count=0,
    )
    session.add(job)
    session.commit()
    session.refresh(job)
    return job


def run_comparison_job(session: Session, job_id: uuid.UUID) -> dict[str, object]:
    job = session.get(ComparisonJob, job_id)
    if job is None:
        raise LookupError(f"Comparison job not found: {job_id}")

    job.status = ComparisonJobStatus.RUNNING
    job.attempts += 1
    if job.started_at is None:
        job.started_at = datetime.now(UTC)
    job.error_message = None
    session.commit()

    try:
        # Clear prior changes if re-running a failed job.
        for existing in list(job.changes):
            session.delete(existing)
        session.flush()

        base_reqs = _load_requirements(session, job.base_document_version_id)
        target_reqs = _load_requirements(session, job.target_document_version_id)
        pairs = align_requirements(base_reqs, target_reqs)
        job.progress_pct = 50
        session.commit()

        for pair in pairs:
            # Skip identical pairs with no meaningful delta (still link quotes for clarity).
            if (
                pair.base is not None
                and pair.target is not None
                and pair.base.statement.strip() == pair.target.statement.strip()
                and pair.base.priority == pair.target.priority
                and pair.category.value == "clarified"
                and (pair.base.acceptance_criteria or []) == (pair.target.acceptance_criteria or [])
            ):
                # Treat exact duplicates as no-op (do not clutter change list).
                continue
            change = RequirementChange(
                comparison_job_id=job.id,
                category=pair.category,
                base_requirement_id=pair.base.id if pair.base else None,
                target_requirement_id=pair.target.id if pair.target else None,
                similarity=pair.similarity,
                old_statement=pair.base.statement if pair.base else None,
                new_statement=pair.target.statement if pair.target else None,
                old_source_quote=source_quote(pair.base) if pair.base else None,
                new_source_quote=source_quote(pair.target) if pair.target else None,
                decision=ChangeDecision.PENDING,
                is_eval_example=False,
            )
            # Source text linkage rule: add/remove may have one side null; others need both.
            if pair.category.value not in {"added", "removed"} and (
                not change.old_source_quote or not change.new_source_quote
            ):
                # Fall back to statements so every non add/remove change has both texts.
                change.old_source_quote = change.old_source_quote or change.old_statement
                change.new_source_quote = change.new_source_quote or change.new_statement
            session.add(change)

        job.change_count = len(job.changes)  # may be stale until flush
        session.flush()
        job.change_count = len(
            session.scalars(
                select(RequirementChange).where(RequirementChange.comparison_job_id == job.id)
            ).all()
        )
        job.status = ComparisonJobStatus.SUCCEEDED
        job.progress_pct = 100
        job.finished_at = datetime.now(UTC)
        session.commit()
        logger.info(
            "comparison_job_succeeded",
            extra={
                "job_id": str(job.id),
                "change_count": job.change_count,
            },
        )
        return {
            "status": "succeeded",
            "job_id": str(job.id),
            "change_count": job.change_count,
        }
    except Exception as exc:  # noqa: BLE001
        job.status = ComparisonJobStatus.FAILED
        job.error_message = str(exc)[:2000]
        session.commit()
        logger.exception("comparison_job_failed", extra={"job_id": str(job.id)})
        return {"status": "failed", "job_id": str(job.id), "error": str(exc)}


def get_comparison_job(session: Session, job_id: uuid.UUID) -> ComparisonJob:
    job = session.scalar(
        select(ComparisonJob)
        .where(ComparisonJob.id == job_id)
        .options(selectinload(ComparisonJob.changes))
    )
    if job is None:
        raise CompareError(f"Comparison job not found: {job_id}")
    return job


def decide_change(
    session: Session,
    change_id: uuid.UUID,
    *,
    decision: str,
) -> RequirementChange:
    change = session.get(RequirementChange, change_id)
    if change is None:
        raise CompareError(f"Requirement change not found: {change_id}")
    new_decision = ChangeDecision(decision)
    if new_decision not in {ChangeDecision.CONFIRMED, ChangeDecision.REJECTED}:
        raise CompareError("decision must be 'confirmed' or 'rejected'")
    change.decision = new_decision
    change.is_eval_example = new_decision == ChangeDecision.CONFIRMED
    session.commit()
    session.refresh(change)
    return change


def _load_requirements(session: Session, document_version_id: uuid.UUID) -> list[Requirement]:
    return list(
        session.scalars(
            select(Requirement)
            .where(Requirement.document_version_id == document_version_id)
            .order_by(Requirement.created_at.asc())
        ).all()
    )
