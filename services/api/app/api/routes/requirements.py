"""Requirement extraction and review endpoints."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.api.schemas import (
    EditRequirementRequest,
    ExtractionJobResponse,
    RequirementResponse,
    StartExtractionResponse,
)
from app.db.session import get_session
from app.extraction.pipeline import ExtractionError, create_extraction_job
from app.extraction.service import (
    edit_requirement,
    export_requirements,
    get_extraction_job,
    list_requirements,
)
from app.ingestion.queue import enqueue_extraction_job

router = APIRouter(tags=["requirements"])


@router.post(
    "/documents/versions/{document_version_id}/extractions",
    response_model=StartExtractionResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def start_extraction(
    document_version_id: uuid.UUID,
    session: Session = Depends(get_session),
) -> StartExtractionResponse:
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
) -> ExtractionJobResponse:
    try:
        job = get_extraction_job(session, job_id)
    except ExtractionError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
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
) -> list[RequirementResponse]:
    try:
        rows = list_requirements(
            session,
            workspace_id=workspace_id,
            document_id=document_id,
            document_version_id=document_version_id,
            review_state=review_state,
            requirement_type=requirement_type,
            limit=limit,
            offset=offset,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return [RequirementResponse.model_validate(row) for row in rows]


@router.patch("/requirements/{requirement_id}", response_model=RequirementResponse)
def patch_requirement(
    requirement_id: uuid.UUID,
    body: EditRequirementRequest,
    session: Session = Depends(get_session),
) -> RequirementResponse:
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
        )
    except ExtractionError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return RequirementResponse.model_validate(row)


@router.get("/requirements/export")
def export_requirements_endpoint(
    format: str = Query(default="json", pattern="^(json|csv)$"),
    workspace_id: uuid.UUID | None = None,
    document_version_id: uuid.UUID | None = None,
    review_state: str | None = None,
    session: Session = Depends(get_session),
) -> Response:
    try:
        media_type, body = export_requirements(
            session,
            format=format,
            workspace_id=workspace_id,
            document_version_id=document_version_id,
            review_state=review_state,
        )
    except ExtractionError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    filename = "requirements.json" if format == "json" else "requirements.csv"
    return Response(
        content=body,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
