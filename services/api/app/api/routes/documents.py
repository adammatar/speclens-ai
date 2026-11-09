"""Document upload, status, delete, and reprocess endpoints."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.schemas import (
    ChunkResponse,
    DocumentResponse,
    DocumentVersionResponse,
    JobStatusResponse,
    ReprocessResponse,
    UploadAcceptedResponse,
)
from app.db.models import Chunk, DocumentVersion, IngestionJob, WorkspaceRole
from app.db.session import get_session
from app.ingestion.errors import DuplicateDocumentError, NotFoundError
from app.ingestion.queue import enqueue_ingest_job
from app.ingestion.service import (
    DEFAULT_WORKSPACE_ID,
    count_chunks,
    delete_document,
    get_document,
    reprocess_document_version,
    upload_document,
    upload_document_version,
)
from app.ingestion.validate import UploadValidationError
from app.security.audit import record_audit
from app.security.auth import AuthContext, require_api_key
from app.security.rate_limit import check_rate_limit
from app.security.workspace import require_workspace_role

router = APIRouter(prefix="/documents", tags=["documents"])


@router.post(
    "/upload",
    response_model=UploadAcceptedResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def upload_document_endpoint(
    request: Request,
    file: UploadFile = File(...),
    title: str | None = Form(default=None),
    session: Session = Depends(get_session),
    auth: AuthContext = Depends(require_api_key),
) -> UploadAcceptedResponse:
    check_rate_limit(request, "upload")
    require_workspace_role(auth, DEFAULT_WORKSPACE_ID, WorkspaceRole.EDITOR)
    raw = await file.read()
    try:
        result = upload_document(
            session,
            filename=file.filename or "upload.bin",
            content_type=file.content_type,
            data=raw,
            title=title,
            workspace_id=DEFAULT_WORKSPACE_ID,
        )
    except DuplicateDocumentError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "message": "Duplicate document content",
                "document_id": exc.document_id,
                "document_version_id": exc.document_version_id,
                "sha256": exc.sha256,
            },
        ) from exc
    except UploadValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    enqueue_ingest_job(result.job_id)
    record_audit(
        session,
        auth=auth,
        action="document.upload",
        workspace_id=DEFAULT_WORKSPACE_ID,
        resource_type="document",
        resource_id=result.document_id,
        detail={"filename": file.filename or "upload.bin", "byte_size": len(raw)},
    )
    return UploadAcceptedResponse(
        document_id=result.document_id,
        document_version_id=result.document_version_id,
        job_id=result.job_id,
        sha256=result.sha256,
    )


@router.get("/jobs/{job_id}", response_model=JobStatusResponse)
def get_job_endpoint(
    job_id: uuid.UUID,
    session: Session = Depends(get_session),
    auth: AuthContext = Depends(require_api_key),
) -> JobStatusResponse:
    job = session.get(IngestionJob, job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    version = session.get(DocumentVersion, job.document_version_id)
    if version is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    require_workspace_role(auth, version.workspace_id, WorkspaceRole.VIEWER)
    return JobStatusResponse(
        id=job.id,
        document_version_id=job.document_version_id,
        status=job.status.value,
        progress_pct=job.progress_pct,
        error_message=job.error_message,
        attempts=job.attempts,
        created_at=job.created_at,
        updated_at=job.updated_at,
        started_at=job.started_at,
        finished_at=job.finished_at,
    )


@router.get(
    "/versions/{document_version_id}/chunks",
    response_model=list[ChunkResponse],
)
def list_chunks_endpoint(
    document_version_id: uuid.UUID,
    session: Session = Depends(get_session),
    auth: AuthContext = Depends(require_api_key),
) -> list[ChunkResponse]:
    version = session.get(DocumentVersion, document_version_id)
    if version is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Version not found")
    require_workspace_role(auth, version.workspace_id, WorkspaceRole.VIEWER)
    chunks = session.scalars(
        select(Chunk)
        .where(Chunk.document_version_id == document_version_id)
        .order_by(Chunk.chunk_index.asc())
    ).all()
    return [
        ChunkResponse(
            id=chunk.id,
            chunk_index=chunk.chunk_index,
            text=chunk.text,
            heading_path=chunk.heading_path,
            page_number=chunk.page_number,
            start_offset=chunk.start_offset,
            end_offset=chunk.end_offset,
            token_count=chunk.token_count,
        )
        for chunk in chunks
    ]


@router.post(
    "/versions/{document_version_id}/reprocess",
    response_model=ReprocessResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def reprocess_endpoint(
    document_version_id: uuid.UUID,
    session: Session = Depends(get_session),
    auth: AuthContext = Depends(require_api_key),
) -> ReprocessResponse:
    version = session.get(DocumentVersion, document_version_id)
    if version is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Version not found")
    require_workspace_role(auth, version.workspace_id, WorkspaceRole.EDITOR)
    try:
        result = reprocess_document_version(session, document_version_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    enqueue_ingest_job(result.job_id)
    return ReprocessResponse(
        document_id=result.document_id,
        document_version_id=result.document_version_id,
        job_id=result.job_id,
    )


@router.post(
    "/{document_id}/versions",
    response_model=UploadAcceptedResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def upload_document_version_endpoint(
    request: Request,
    document_id: uuid.UUID,
    file: UploadFile = File(...),
    session: Session = Depends(get_session),
    auth: AuthContext = Depends(require_api_key),
) -> UploadAcceptedResponse:
    check_rate_limit(request, "upload")
    try:
        document = get_document(session, document_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    require_workspace_role(auth, document.workspace_id, WorkspaceRole.EDITOR)
    raw = await file.read()
    try:
        result = upload_document_version(
            session,
            document_id,
            filename=file.filename or "upload.bin",
            content_type=file.content_type,
            data=raw,
        )
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except DuplicateDocumentError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "message": "Duplicate document content",
                "document_id": exc.document_id,
                "document_version_id": exc.document_version_id,
                "sha256": exc.sha256,
            },
        ) from exc
    except UploadValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    enqueue_ingest_job(result.job_id)
    record_audit(
        session,
        auth=auth,
        action="document.version_upload",
        workspace_id=document.workspace_id,
        resource_type="document_version",
        resource_id=result.document_version_id,
        detail={"filename": file.filename or "upload.bin", "byte_size": len(raw)},
    )
    return UploadAcceptedResponse(
        document_id=result.document_id,
        document_version_id=result.document_version_id,
        job_id=result.job_id,
        sha256=result.sha256,
    )


@router.get("/{document_id}", response_model=DocumentResponse)
def get_document_endpoint(
    document_id: uuid.UUID,
    session: Session = Depends(get_session),
    auth: AuthContext = Depends(require_api_key),
) -> DocumentResponse:
    try:
        document = get_document(session, document_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    require_workspace_role(auth, document.workspace_id, WorkspaceRole.VIEWER)

    versions: list[DocumentVersionResponse] = []
    for version in document.versions:
        versions.append(
            DocumentVersionResponse(
                id=version.id,
                version_number=version.version_number,
                filename=version.filename,
                content_type=version.content_type,
                byte_size=version.byte_size,
                sha256=version.sha256,
                status=version.status.value,
                error_message=version.error_message,
                page_count=version.page_count,
                created_at=version.created_at,
                chunk_count=count_chunks(session, version.id),
            )
        )
    return DocumentResponse(
        id=document.id,
        workspace_id=document.workspace_id,
        title=document.title,
        created_at=document.created_at,
        updated_at=document.updated_at,
        versions=versions,
    )


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document_endpoint(
    document_id: uuid.UUID,
    session: Session = Depends(get_session),
    auth: AuthContext = Depends(require_api_key),
) -> None:
    try:
        document = get_document(session, document_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    require_workspace_role(auth, document.workspace_id, WorkspaceRole.EDITOR)
    workspace_id = document.workspace_id
    try:
        delete_document(session, document_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    record_audit(
        session,
        auth=auth,
        action="document.delete",
        workspace_id=workspace_id,
        resource_type="document",
        resource_id=document_id,
    )
