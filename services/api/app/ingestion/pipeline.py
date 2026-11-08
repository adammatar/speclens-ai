"""Ingestion pipeline executed by the worker."""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.models import (
    Chunk,
    DocumentVersion,
    DocumentVersionStatus,
    IngestionJob,
    IngestionJobStatus,
)
from app.ingestion.chunking import chunk_document
from app.ingestion.errors import ParseError
from app.ingestion.parsers import parse_document
from app.ingestion.types import SupportedKind
from app.storage.filesystem import StorageInterface, get_storage

logger = logging.getLogger(__name__)


def _kind_from_version(version: DocumentVersion) -> SupportedKind:
    name = version.filename.lower()
    if name.endswith((".md", ".markdown")):
        return "markdown"
    if name.endswith(".docx"):
        return "docx"
    if name.endswith(".pdf"):
        return "pdf"
    raise ParseError(f"Cannot infer parser kind for {version.filename}")


def run_ingestion_job(
    session: Session,
    job_id: uuid.UUID,
    *,
    storage: StorageInterface | None = None,
) -> dict[str, object]:
    """Parse, chunk, and persist a document version for the given job."""
    job = session.get(IngestionJob, job_id)
    if job is None:
        raise LookupError(f"Ingestion job not found: {job_id}")

    version = session.get(DocumentVersion, job.document_version_id)
    if version is None:
        raise LookupError(f"Document version not found: {job.document_version_id}")

    job.status = IngestionJobStatus.RUNNING
    job.attempts += 1
    job.progress_pct = 5
    job.started_at = datetime.now(UTC)
    job.error_message = None
    version.status = DocumentVersionStatus.PROCESSING
    version.error_message = None
    session.commit()

    try:
        store = storage or get_storage(get_settings())
        data = store.get_bytes(version.storage_key)
        job.progress_pct = 25
        session.commit()

        kind = _kind_from_version(version)
        parsed = parse_document(filename=version.filename, kind=kind, data=data)
        job.progress_pct = 55
        session.commit()

        drafts = chunk_document(parsed)
        job.progress_pct = 75
        session.commit()

        # Replace prior chunks (supports reprocess).
        session.execute(delete(Chunk).where(Chunk.document_version_id == version.id))
        for draft in drafts:
            session.add(
                Chunk(
                    document_version_id=version.id,
                    chunk_index=draft.chunk_index,
                    text=draft.text,
                    heading_path=draft.heading_path,
                    page_number=draft.page_number,
                    start_offset=draft.start_offset,
                    end_offset=draft.end_offset,
                    token_count=draft.token_count,
                )
            )

        version.page_count = parsed.page_count
        version.status = DocumentVersionStatus.READY
        job.status = IngestionJobStatus.SUCCEEDED
        job.progress_pct = 100
        job.finished_at = datetime.now(UTC)
        session.commit()

        logger.info(
            "ingestion_succeeded",
            extra={
                "job_id": str(job.id),
                "document_version_id": str(version.id),
                "chunk_count": len(drafts),
            },
        )
        return {
            "status": "succeeded",
            "job_id": str(job.id),
            "document_version_id": str(version.id),
            "chunk_count": len(drafts),
        }
    except Exception as exc:  # noqa: BLE001 - persist failure state
        session.rollback()
        job = session.get(IngestionJob, job_id)
        version = session.get(DocumentVersion, job.document_version_id) if job else None
        message = str(exc)
        if job is not None:
            job.status = IngestionJobStatus.FAILED
            job.error_message = message
            job.progress_pct = max(job.progress_pct, 0)
            job.finished_at = datetime.now(UTC)
        if version is not None:
            version.status = DocumentVersionStatus.FAILED
            version.error_message = message
        session.commit()
        logger.exception("ingestion_failed", extra={"job_id": str(job_id)})
        raise


def get_job(session: Session, job_id: uuid.UUID) -> IngestionJob | None:
    return session.scalar(select(IngestionJob).where(IngestionJob.id == job_id))
