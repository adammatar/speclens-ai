"""Version comparison endpoints."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, status
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
from app.db.models import DocumentVersion, RequirementChange, WorkspaceRole
from app.db.session import get_session
from app.ingestion.queue import enqueue_comparison_job
from app.security.audit import record_audit
from app.security.auth import AuthContext, require_api_key
from app.security.rate_limit import check_rate_limit
from app.security.workspace import require_workspace_role

router = APIRouter(prefix="/comparisons", tags=["comparisons"])


@router.post("", response_model=StartComparisonResponse, status_code=status.HTTP_202_ACCEPTED)
def start_comparison(
    request: Request,
    body: CreateComparisonRequest,
    session: Session = Depends(get_session),
    auth: AuthContext = Depends(require_api_key),
) -> StartComparisonResponse:
    check_rate_limit(request, "compare")
    base = session.get(DocumentVersion, body.base_document_version_id)
    target = session.get(DocumentVersion, body.target_document_version_id)
    if base is None or target is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="version not found")
    require_workspace_role(auth, base.workspace_id, WorkspaceRole.EDITOR)
    require_workspace_role(auth, target.workspace_id, WorkspaceRole.EDITOR)
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
    auth: AuthContext = Depends(require_api_key),
) -> ComparisonJobResponse:
    try:
        job = get_comparison_job(session, job_id)
    except CompareError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    require_workspace_role(auth, job.workspace_id, WorkspaceRole.VIEWER)
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
    auth: AuthContext = Depends(require_api_key),
) -> RequirementChangeResponse:
    change = session.get(RequirementChange, change_id)
    if change is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Change not found")
    job = get_comparison_job(session, change.comparison_job_id)
    require_workspace_role(auth, job.workspace_id, WorkspaceRole.EDITOR)
    try:
        updated = decide_change(session, change_id, decision=body.decision)
    except CompareError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    if body.decision == "confirmed":
        record_audit(
            session,
            auth=auth,
            action="comparison.change_confirm",
            workspace_id=job.workspace_id,
            resource_type="requirement_change",
            resource_id=updated.id,
        )
    return RequirementChangeResponse.model_validate(updated)
