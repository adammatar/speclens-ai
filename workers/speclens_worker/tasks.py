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


@app.task(name="speclens.ingest_document", bind=True, max_retries=3, default_retry_delay=5)  # type: ignore[untyped-decorator]
def ingest_document(self: Any, job_id: str) -> dict[str, object]:
    """Run the document ingestion pipeline for a queued job."""
    from app.db.session import get_session_factory
    from app.ingestion.errors import ParseError
    from app.ingestion.pipeline import run_ingestion_job

    session = get_session_factory()()
    try:
        return run_ingestion_job(session, uuid.UUID(job_id))
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
