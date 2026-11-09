"""Resumable section-oriented requirement extraction pipeline."""

from __future__ import annotations

import logging
import uuid
from collections import OrderedDict
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.db.models import (
    Chunk,
    DocumentVersion,
    DocumentVersionStatus,
    ExtractionJob,
    ExtractionJobStatus,
    Requirement,
    RequirementPriority,
    RequirementReviewState,
    RequirementType,
)
from app.extraction.base import SectionInput
from app.extraction.factory import get_extractor
from app.extraction.schema import RequirementDraft

logger = logging.getLogger(__name__)


class ExtractionError(ValueError):
    """Raised for invalid extraction requests."""


def create_extraction_job(
    session: Session,
    document_version_id: uuid.UUID,
    *,
    settings: Settings | None = None,
) -> ExtractionJob:
    cfg = settings or get_settings()
    version = session.get(DocumentVersion, document_version_id)
    if version is None:
        raise ExtractionError(f"Document version not found: {document_version_id}")
    if version.status != DocumentVersionStatus.READY:
        raise ExtractionError(
            f"Document version must be ready before extraction (status={version.status.value})"
        )
    sections = _group_sections(session, version)
    job = ExtractionJob(
        document_version_id=version.id,
        workspace_id=version.workspace_id,
        status=ExtractionJobStatus.QUEUED,
        progress_pct=0,
        section_cursor=0,
        section_total=len(sections),
        model_name=cfg.extraction_model,
        prompt_version=cfg.extraction_prompt_version,
    )
    session.add(job)
    session.commit()
    session.refresh(job)
    return job


def run_extraction_job(
    session: Session,
    job_id: uuid.UUID,
    *,
    settings: Settings | None = None,
    fail_after_sections: int | None = None,
) -> dict[str, object]:
    """Process remaining sections for a job. Resumes from section_cursor."""
    cfg = settings or get_settings()
    job = session.get(ExtractionJob, job_id)
    if job is None:
        raise LookupError(f"Extraction job not found: {job_id}")

    version = session.get(DocumentVersion, job.document_version_id)
    if version is None:
        job.status = ExtractionJobStatus.FAILED
        job.error_message = "document version missing"
        job.finished_at = datetime.now(UTC)
        session.commit()
        raise LookupError(job.error_message)

    sections = _group_sections(session, version)
    job.section_total = len(sections)
    job.status = ExtractionJobStatus.RUNNING
    job.attempts += 1
    if job.started_at is None:
        job.started_at = datetime.now(UTC)
    job.error_message = None
    session.commit()

    extractor = get_extractor(cfg)
    job.model_name = extractor.model_name
    job.prompt_version = extractor.prompt_version

    processed_this_run = 0
    try:
        for index in range(job.section_cursor, len(sections)):
            if fail_after_sections is not None and processed_this_run >= fail_after_sections:
                raise RuntimeError("simulated extraction failure for resume testing")
            section = sections[index]
            drafts = extractor.extract_section(section)
            for draft in drafts:
                _persist_draft(session, job, version, draft)
            job.section_cursor = index + 1
            processed_this_run += 1
            if job.section_total:
                job.progress_pct = int(100 * job.section_cursor / job.section_total)
            session.commit()
    except Exception as exc:  # noqa: BLE001 - persist failure, allow resume
        job.status = ExtractionJobStatus.FAILED
        job.error_message = str(exc)[:2000]
        session.commit()
        logger.exception(
            "extraction_job_failed",
            extra={
                "job_id": str(job.id),
                "section_cursor": job.section_cursor,
            },
        )
        return {
            "status": "failed",
            "job_id": str(job.id),
            "section_cursor": job.section_cursor,
            "error": str(exc),
        }

    job.status = ExtractionJobStatus.SUCCEEDED
    job.progress_pct = 100
    job.finished_at = datetime.now(UTC)
    session.commit()
    logger.info(
        "extraction_job_succeeded",
        extra={
            "job_id": str(job.id),
            "document_version_id": str(version.id),
            "section_total": job.section_total,
            # Intentionally omit raw document text.
        },
    )
    return {
        "status": "succeeded",
        "job_id": str(job.id),
        "section_cursor": job.section_cursor,
        "section_total": job.section_total,
    }


def _group_sections(session: Session, version: DocumentVersion) -> list[SectionInput]:
    chunks = session.scalars(
        select(Chunk)
        .where(Chunk.document_version_id == version.id)
        .order_by(Chunk.chunk_index.asc())
    ).all()
    grouped: OrderedDict[str, list[Chunk]] = OrderedDict()
    for chunk in chunks:
        key = chunk.heading_path or f"chunk-{chunk.chunk_index}"
        grouped.setdefault(key, []).append(chunk)
    sections: list[SectionInput] = []
    for path, group in grouped.items():
        text = "\n\n".join(chunk.text for chunk in group)
        page = next((c.page_number for c in group if c.page_number is not None), None)
        sections.append(
            SectionInput(
                section_path=path,
                text=text,
                page_number=page,
                document_id=version.document_id,
                document_version_id=version.id,
            )
        )
    return sections


def _persist_draft(
    session: Session,
    job: ExtractionJob,
    version: DocumentVersion,
    draft: RequirementDraft,
) -> Requirement:
    # Re-validate at persist boundary (schema validation is mandatory).
    validated = RequirementDraft.model_validate(draft.model_dump())
    payload = validated.model_dump(mode="json")
    requirement = Requirement(
        workspace_id=version.workspace_id,
        document_id=version.document_id,
        document_version_id=version.id,
        extraction_job_id=job.id,
        section_path=validated.section_path or "",
        external_id=validated.external_id,
        requirement_type=RequirementType(validated.requirement_type),
        statement=validated.statement,
        rationale=validated.rationale,
        priority=RequirementPriority(validated.priority),
        acceptance_criteria=[c.model_dump(mode="json") for c in validated.acceptance_criteria],
        dependencies=list(validated.dependencies),
        ambiguities=list(validated.ambiguities),
        contradiction_candidates=list(validated.contradiction_candidates),
        confidence=validated.confidence,
        sources=[s.model_dump(mode="json") for s in validated.sources],
        review_state=RequirementReviewState.PROPOSED,
        original_payload=payload,
        is_eval_example=False,
    )
    session.add(requirement)
    return requirement
