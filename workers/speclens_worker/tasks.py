"""Worker task definitions."""

from __future__ import annotations

import logging
import uuid
from typing import Any

from speclens_worker.celery_app import app

logger = logging.getLogger(__name__)


@app.task(name="speclens.noop")  # type: ignore[untyped-decorator]
def noop_job(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    """No-op job used to prove the worker can dequeue and acknowledge work."""
    data = payload or {}
    logger.info("noop_job_executed", extra={"payload_keys": sorted(data.keys())})
    return {"status": "ok", "echo": data}


@app.task(name="speclens.retention_sweep")  # type: ignore[untyped-decorator]
def retention_sweep(dry_run: bool = True) -> dict[str, Any]:
    """Delete documents older than RETENTION_DAYS (disabled unless explicitly enabled)."""
    from app.core.config import get_settings
    from app.db.session import get_session_factory
    from app.retention.service import run_retention_sweep

    settings = get_settings()
    if not dry_run and not settings.retention_sweep_enabled:
        logger.warning("retention_sweep_skipped_disabled")
        return {"status": "skipped", "reason": "RETENTION_SWEEP_ENABLED is false"}
    session = get_session_factory()()
    try:
        result = run_retention_sweep(session, dry_run=dry_run, settings=settings)
        return {
            "status": "ok",
            "dry_run": result.dry_run,
            "candidates": len(result.candidates),
            "deleted": len(result.deleted_ids),
            "errors": result.errors,
        }
    finally:
        session.close()


@app.task(name="speclens.embed_document_version", bind=True, max_retries=3, default_retry_delay=5)  # type: ignore[untyped-decorator]
def embed_document_version(self: Any, document_version_id: str) -> dict[str, object]:
    """Embed all chunks for a document version."""
    from app.db.session import get_session_factory
    from app.embeddings.pipeline import run_embed_document_version

    session = get_session_factory()()
    try:
        return run_embed_document_version(session, uuid.UUID(document_version_id))
    except LookupError as exc:
        logger.error(
            "embed_document_permanent_failure",
            extra={"document_version_id": document_version_id, "error": str(exc)},
        )
        return {
            "status": "failed",
            "document_version_id": document_version_id,
            "error": str(exc),
        }
    except Exception as exc:  # noqa: BLE001
        logger.exception(
            "embed_document_task_failed",
            extra={"document_version_id": document_version_id},
        )
        raise self.retry(exc=exc) from exc
    finally:
        session.close()


@app.task(
    name="speclens.compare_document_versions", bind=True, max_retries=3, default_retry_delay=5
)  # type: ignore[untyped-decorator]
def compare_document_versions(self: Any, job_id: str) -> dict[str, object]:
    """Compare extracted requirements across two document versions."""
    from app.compare.pipeline import CompareError, run_comparison_job
    from app.db.session import get_session_factory

    session = get_session_factory()()
    try:
        return run_comparison_job(session, uuid.UUID(job_id))
    except (CompareError, LookupError) as exc:
        logger.error(
            "compare_document_versions_permanent_failure",
            extra={"job_id": job_id, "error": str(exc)},
        )
        return {"status": "failed", "job_id": job_id, "error": str(exc)}
    except Exception as exc:  # noqa: BLE001
        logger.exception("compare_document_versions_task_failed", extra={"job_id": job_id})
        raise self.retry(exc=exc) from exc
    finally:
        session.close()


@app.task(name="speclens.extract_requirements", bind=True, max_retries=3, default_retry_delay=5)  # type: ignore[untyped-decorator]
def extract_requirements(self: Any, job_id: str) -> dict[str, object]:
    """Run resumable requirement extraction for a document version."""
    from app.db.session import get_session_factory
    from app.extraction.pipeline import ExtractionError, run_extraction_job

    session = get_session_factory()()
    try:
        return run_extraction_job(session, uuid.UUID(job_id))
    except (ExtractionError, LookupError) as exc:
        logger.error(
            "extract_requirements_permanent_failure",
            extra={"job_id": job_id, "error": str(exc)},
        )
        return {"status": "failed", "job_id": job_id, "error": str(exc)}
    except Exception as exc:  # noqa: BLE001
        logger.exception("extract_requirements_task_failed", extra={"job_id": job_id})
        raise self.retry(exc=exc) from exc
    finally:
        session.close()


@app.task(name="speclens.ingest_document", bind=True, max_retries=3, default_retry_delay=5)  # type: ignore[untyped-decorator]
def ingest_document(self: Any, job_id: str) -> dict[str, object]:
    """Run the document ingestion pipeline for a queued job."""
    from app.db.session import get_session_factory
    from app.ingestion.errors import ParseError
    from app.ingestion.pipeline import run_ingestion_job

    session = get_session_factory()()
    try:
        result = run_ingestion_job(session, uuid.UUID(job_id))
        version_id = result.get("document_version_id")
        if result.get("status") == "succeeded" and version_id:
            # Chain embedding without blocking the API upload path.
            embed_document_version.delay(str(version_id))
        return result
    except (ParseError, LookupError) as exc:
        # Permanent failures are already persisted by the pipeline.
        logger.error(
            "ingest_document_permanent_failure",
            extra={"job_id": job_id, "error": str(exc)},
        )
        return {"status": "failed", "job_id": job_id, "error": str(exc)}
    except Exception as exc:  # noqa: BLE001 - retry transient failures
        logger.exception("ingest_document_task_failed", extra={"job_id": job_id})
        raise self.retry(exc=exc) from exc
    finally:
        session.close()
