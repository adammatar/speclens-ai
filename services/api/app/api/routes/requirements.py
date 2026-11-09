"""Requirement extraction and review endpoints."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.api.schemas import (
    EditRequirementRequest,
    ExtractionJobResponse,
    RequirementResponse,
    StartExtractionResponse,
)
from app.db.models import DocumentVersion, Requirement, WorkspaceRole
from app.db.session import get_session
from app.extraction.pipeline import ExtractionError, create_extraction_job
from app.extraction.service import (
    edit_requirement,
    export_requirements,
    get_extraction_job,
    list_requirements,
)
from app.ingestion.queue import enqueue_extraction_job
from app.ingestion.service import DEFAULT_WORKSPACE_ID
from app.security.audit import record_audit
from app.security.auth import AuthContext, require_api_key
from app.security.rate_limit import check_rate_limit
from app.security.workspace import require_workspace_role

router = APIRouter(tags=["requirements"])


@router.post(
    "/documents/versions/{document_version_id}/extractions",
    response_model=StartExtractionResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def start_extraction(
    request: Request,
    document_version_id: uuid.UUID,
    session: Session = Depends(get_session),
    auth: AuthContext = Depends(require_api_key),
) -> StartExtractionResponse:
    check_rate_limit(request, "extract")
    version = session.get(DocumentVersion, document_version_id)
    if version is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Version not found")
    require_workspace_role(auth, version.workspace_id, WorkspaceRole.EDITOR)
    try:
        job = create_extraction_job(session, document_version_id)
    except ExtractionError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    enqueue_extraction_job(job.id)
    return StartExtractionResponse(
        job_id=job.id,
        document_version_id=job.document_version_id,
        status=job.status.value,
    )


@router.get("/extractions/{job_id}", response_model=ExtractionJobResponse)
def get_extraction(
    job_id: uuid.UUID,
    session: Session = Depends(get_session),
    auth: AuthContext = Depends(require_api_key),
) -> ExtractionJobResponse:
    try:
        job = get_extraction_job(session, job_id)
    except ExtractionError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    require_workspace_role(auth, job.workspace_id, WorkspaceRole.VIEWER)
    return ExtractionJobResponse.model_validate(job)


@router.get("/requirements", response_model=list[RequirementResponse])
def list_requirements_endpoint(
    workspace_id: uuid.UUID | None = None,
    document_id: uuid.UUID | None = None,
    document_version_id: uuid.UUID | None = None,
    review_state: str | None = None,
    requirement_type: str | None = None,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    session: Session = Depends(get_session),
    auth: AuthContext = Depends(require_api_key),
) -> list[RequirementResponse]:
    ws = workspace_id or DEFAULT_WORKSPACE_ID
    require_workspace_role(auth, ws, WorkspaceRole.VIEWER)
    try:
        rows = list_requirements(
            session,
            workspace_id=ws,
            document_id=document_id,
            document_version_id=document_version_id,
            review_state=review_state,
            requirement_type=requirement_type,
            limit=limit,
            offset=offset,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    # Defense in depth: drop any row outside caller's workspaces.
    rows = [row for row in rows if row.workspace_id in auth.workspace_ids]
    return [RequirementResponse.model_validate(row) for row in rows]


@router.patch("/requirements/{requirement_id}", response_model=RequirementResponse)
def patch_requirement(
    requirement_id: uuid.UUID,
    body: EditRequirementRequest,
    session: Session = Depends(get_session),
    auth: AuthContext = Depends(require_api_key),
) -> RequirementResponse:
    existing = session.get(Requirement, requirement_id)
    if existing is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Requirement not found")
    require_workspace_role(auth, existing.workspace_id, WorkspaceRole.EDITOR)
    try:
        row = edit_requirement(
            session,
            requirement_id,
            statement=body.statement,
            rationale=body.rationale,
            requirement_type=body.requirement_type,
            priority=body.priority,
            acceptance_criteria=body.acceptance_criteria,
            dependencies=body.dependencies,
            ambiguities=body.ambiguities,
            review_state=body.review_state,
            jira_ticket_id=body.jira_ticket_id,
            source_file=body.source_file,
            test_case_id=body.test_case_id,
            implementation_note=body.implementation_note,
        )
    except ExtractionError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    if body.review_state == "accepted":
        record_audit(
            session,
            auth=auth,
            action="requirement.accept",
            workspace_id=row.workspace_id,
            resource_type="requirement",
            resource_id=row.id,
        )
    return RequirementResponse.model_validate(row)


@router.get("/requirements/export")
def export_requirements_endpoint(
    format: str = Query(default="json", pattern="^(json|csv)$"),
    workspace_id: uuid.UUID | None = None,
    document_version_id: uuid.UUID | None = None,
    review_state: str | None = None,
    session: Session = Depends(get_session),
    auth: AuthContext = Depends(require_api_key),
) -> Response:
    ws = workspace_id or DEFAULT_WORKSPACE_ID
    require_workspace_role(auth, ws, WorkspaceRole.VIEWER)
    try:
        media_type, body = export_requirements(
            session,
            format=format,
            workspace_id=ws,
            document_version_id=document_version_id,
            review_state=review_state,
        )
    except ExtractionError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    record_audit(
        session,
        auth=auth,
        action="requirement.export",
        workspace_id=ws,
        resource_type="requirements",
        detail={"format": format},
    )
    filename = "requirements.json" if format == "json" else "requirements.csv"
    return Response(
        content=body,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
