"""API-facing ingestion orchestration (upload, delete, reprocess)."""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.db.models import (
    Document,
    DocumentVersion,
    DocumentVersionStatus,
    IngestionJob,
    IngestionJobStatus,
    Workspace,
)
from app.ingestion.errors import DuplicateDocumentError, NotFoundError
from app.ingestion.hashing import sha256_hex
from app.ingestion.validate import ValidatedUpload, validate_upload
from app.storage.filesystem import StorageInterface, get_storage

logger = logging.getLogger(__name__)

DEFAULT_WORKSPACE_ID = uuid.UUID("00000000-0000-4000-8000-000000000001")


@dataclass(frozen=True, slots=True)
class UploadResult:
    document_id: uuid.UUID
    document_version_id: uuid.UUID
    job_id: uuid.UUID
    sha256: str
    deduplicated: bool = False


def ensure_default_workspace(session: Session) -> Workspace:
    workspace = session.get(Workspace, DEFAULT_WORKSPACE_ID)
    if workspace is not None:
        return workspace
    workspace = Workspace(id=DEFAULT_WORKSPACE_ID, name="default")
    session.add(workspace)
    session.flush()
    return workspace


def _storage_key(workspace_id: uuid.UUID, version_id: uuid.UUID, filename: str) -> str:
    safe_name = filename.replace("/", "_").replace("\\", "_")
    return f"workspaces/{workspace_id}/versions/{version_id}/{safe_name}"


def upload_document(
    session: Session,
    *,
    filename: str,
    content_type: str | None,
    data: bytes,
    title: str | None = None,
    workspace_id: uuid.UUID | None = None,
    settings: Settings | None = None,
    storage: StorageInterface | None = None,
) -> UploadResult:
    """Validate, store, create records, and enqueue an ingestion job id (caller enqueues Celery)."""
    cfg = settings or get_settings()
    store = storage or get_storage(cfg)
    validated: ValidatedUpload = validate_upload(
        filename=filename,
        content_type=content_type,
        size=len(data),
        max_bytes=cfg.max_upload_bytes,
    )
    digest = sha256_hex(data)
    workspace = session.get(Workspace, workspace_id or DEFAULT_WORKSPACE_ID)
    if workspace is None:
        workspace = ensure_default_workspace(session)

    existing = session.scalar(
        select(DocumentVersion).where(
            DocumentVersion.workspace_id == workspace.id,
            DocumentVersion.sha256 == digest,
        )
    )
    if existing is not None:
        raise DuplicateDocumentError(
            document_id=str(existing.document_id),
            document_version_id=str(existing.id),
            sha256=digest,
        )

    document = Document(
        workspace_id=workspace.id,
        title=title or validated.filename,
    )
    session.add(document)
    session.flush()

    version_id = uuid.uuid4()
    key = _storage_key(workspace.id, version_id, validated.filename)
    store.put_bytes(key, data)

    version = DocumentVersion(
        id=version_id,
        document_id=document.id,
        workspace_id=workspace.id,
        version_number=1,
        filename=validated.filename,
        content_type=validated.content_type,
        byte_size=validated.size,
        sha256=digest,
        storage_key=key,
        status=DocumentVersionStatus.PENDING,
    )
    session.add(version)
    session.flush()

    job = IngestionJob(
        document_version_id=version.id,
        status=IngestionJobStatus.QUEUED,
        progress_pct=0,
        attempts=0,
    )
    session.add(job)
    session.commit()

    logger.info(
        "document_uploaded",
        extra={
            "document_id": str(document.id),
            "document_version_id": str(version.id),
            "job_id": str(job.id),
            "sha256": digest,
        },
    )
    return UploadResult(
        document_id=document.id,
        document_version_id=version.id,
        job_id=job.id,
        sha256=digest,
        deduplicated=False,
    )


def upload_document_version(
    session: Session,
    document_id: uuid.UUID,
    *,
    filename: str,
    content_type: str | None,
    data: bytes,
    settings: Settings | None = None,
    storage: StorageInterface | None = None,
) -> UploadResult:
    """Upload a new version of an existing document (Phase 6)."""
    cfg = settings or get_settings()
    store = storage or get_storage(cfg)
    document = session.get(Document, document_id)
    if document is None:
        raise NotFoundError(f"Document not found: {document_id}")

    validated: ValidatedUpload = validate_upload(
        filename=filename,
        content_type=content_type,
        size=len(data),
        max_bytes=cfg.max_upload_bytes,
    )
    digest = sha256_hex(data)
    existing = session.scalar(
        select(DocumentVersion).where(
            DocumentVersion.workspace_id == document.workspace_id,
            DocumentVersion.sha256 == digest,
        )
    )
    if existing is not None:
        raise DuplicateDocumentError(
            document_id=str(existing.document_id),
            document_version_id=str(existing.id),
            sha256=digest,
        )

    latest = session.scalar(
        select(DocumentVersion.version_number)
        .where(DocumentVersion.document_id == document.id)
        .order_by(DocumentVersion.version_number.desc())
        .limit(1)
    )
    next_version = int(latest or 0) + 1
    version_id = uuid.uuid4()
    key = _storage_key(document.workspace_id, version_id, validated.filename)
    store.put_bytes(key, data)

    version = DocumentVersion(
        id=version_id,
        document_id=document.id,
        workspace_id=document.workspace_id,
        version_number=next_version,
        filename=validated.filename,
        content_type=validated.content_type,
        byte_size=validated.size,
        sha256=digest,
        storage_key=key,
        status=DocumentVersionStatus.PENDING,
    )
    session.add(version)
    session.flush()

    job = IngestionJob(
        document_version_id=version.id,
        status=IngestionJobStatus.QUEUED,
        progress_pct=0,
        attempts=0,
    )
    session.add(job)
    session.commit()

    logger.info(
        "document_version_uploaded",
        extra={
            "document_id": str(document.id),
            "document_version_id": str(version.id),
            "job_id": str(job.id),
            "version_number": next_version,
            "sha256": digest,
        },
    )
    return UploadResult(
        document_id=document.id,
        document_version_id=version.id,
        job_id=job.id,
        sha256=digest,
        deduplicated=False,
    )


def delete_document(
    session: Session,
    document_id: uuid.UUID,
    *,
    settings: Settings | None = None,
    storage: StorageInterface | None = None,
) -> None:
    """Delete a document, its versions/chunks/jobs, and object bytes."""
    cfg = settings or get_settings()
    store = storage or get_storage(cfg)
    document = session.get(Document, document_id)
    if document is None:
        raise NotFoundError(f"Document not found: {document_id}")

    versions = list(document.versions)
    for version in versions:
        try:
            store.delete(version.storage_key)
        except Exception:  # noqa: BLE001 - continue deleting DB rows
            logger.warning("storage_delete_failed", extra={"key": version.storage_key})

    session.delete(document)
    session.commit()


def reprocess_document_version(
    session: Session,
    document_version_id: uuid.UUID,
) -> UploadResult:
    """Create a new queued ingestion job for an existing version (retry/reprocess)."""
    version = session.get(DocumentVersion, document_version_id)
    if version is None:
        raise NotFoundError(f"Document version not found: {document_version_id}")

    version.status = DocumentVersionStatus.PENDING
    version.error_message = None
    job = IngestionJob(
        document_version_id=version.id,
        status=IngestionJobStatus.QUEUED,
        progress_pct=0,
        attempts=0,
    )
    session.add(job)
    session.commit()
    return UploadResult(
        document_id=version.document_id,
        document_version_id=version.id,
        job_id=job.id,
        sha256=version.sha256,
        deduplicated=False,
    )


def get_document(session: Session, document_id: uuid.UUID) -> Document:
    document = session.get(Document, document_id)
    if document is None:
        raise NotFoundError(f"Document not found: {document_id}")
    return document


def list_documents(
    session: Session,
    *,
    workspace_id: uuid.UUID,
    limit: int = 50,
    offset: int = 0,
) -> list[Document]:
    """List documents in a workspace (newest first)."""
    from sqlalchemy.orm import selectinload

    return list(
        session.scalars(
            select(Document)
            .where(Document.workspace_id == workspace_id)
            .options(selectinload(Document.versions))
            .order_by(Document.updated_at.desc())
            .limit(limit)
            .offset(offset)
        ).all()
    )


def count_chunks(session: Session, document_version_id: uuid.UUID) -> int:
    from app.db.models import Chunk

    return int(
        session.scalar(
            select(func.count())
            .select_from(Chunk)
            .where(Chunk.document_version_id == document_version_id)
        )
        or 0
    )
