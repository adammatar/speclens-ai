"""Celery enqueue helpers used by the API."""

from __future__ import annotations

import logging
import uuid

from celery import Celery

from app.core.config import get_settings

logger = logging.getLogger(__name__)

_client: Celery | None = None


def get_celery_client() -> Celery:
    """Lazy Celery client for publishing tasks from the API process."""
    global _client
    if _client is None:
        settings = get_settings()
        _client = Celery(
            "speclens-api-producer",
            broker=settings.celery_broker_url,
            backend=settings.celery_result_backend,
        )
        _client.conf.update(
            task_serializer="json", accept_content=["json"], result_serializer="json"
        )
    return _client


def enqueue_ingest_job(job_id: uuid.UUID) -> str:
    """Publish speclens.ingest_document for the given job id."""
    async_result = get_celery_client().send_task(
        "speclens.ingest_document",
        args=[str(job_id)],
    )
    task_id = str(async_result.id)
    logger.info(
        "ingest_job_enqueued",
        extra={"job_id": str(job_id), "celery_task_id": task_id},
    )
    return task_id
