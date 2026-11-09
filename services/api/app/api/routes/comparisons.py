"""Version comparison endpoints."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.schemas import (
    ComparisonJobResponse,
    CreateComparisonRequest,
    DecideChangeRequest,
    RequirementChangeResponse,
    StartComparisonResponse,
)
from app.compare.pipeline import (
    CompareError,
    create_comparison_job,
    decide_change,
    get_comparison_job,
)
from app.db.session import get_session
from app.ingestion.queue import enqueue_comparison_job

router = APIRouter(prefix="/comparisons", tags=["comparisons"])


@router.post("", response_model=StartComparisonResponse, status_code=status.HTTP_202_ACCEPTED)
def start_comparison(
    body: CreateComparisonRequest,
    session: Session = Depends(get_session),
) -> StartComparisonResponse:
    try:
        job = create_comparison_job(
            session,
            base_document_version_id=body.base_document_version_id,
            target_document_version_id=body.target_document_version_id,
        )
    except CompareError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    enqueue_comparison_job(job.id)
    return StartComparisonResponse(
        job_id=job.id,
        status=job.status.value,
        base_document_version_id=job.base_document_version_id,
        target_document_version_id=job.target_document_version_id,
    )


@router.get("/{job_id}", response_model=ComparisonJobResponse)
def get_comparison(
    job_id: uuid.UUID,
    session: Session = Depends(get_session),
) -> ComparisonJobResponse:
    try:
        job = get_comparison_job(session, job_id)
    except CompareError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return ComparisonJobResponse(
        id=job.id,
        workspace_id=job.workspace_id,
        base_document_version_id=job.base_document_version_id,
        target_document_version_id=job.target_document_version_id,
        status=job.status.value,
        progress_pct=job.progress_pct,
        error_message=job.error_message,
        attempts=job.attempts,
        change_count=job.change_count,
        created_at=job.created_at,
        updated_at=job.updated_at,
        started_at=job.started_at,
        finished_at=job.finished_at,
        changes=[RequirementChangeResponse.model_validate(change) for change in job.changes],
    )


@router.patch("/changes/{change_id}", response_model=RequirementChangeResponse)
def patch_change_decision(
    change_id: uuid.UUID,
    body: DecideChangeRequest,
    session: Session = Depends(get_session),
) -> RequirementChangeResponse:
    try:
        change = decide_change(session, change_id, decision=body.decision)
    except CompareError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return RequirementChangeResponse.model_validate(change)
