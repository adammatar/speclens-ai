"""Retention sweep: delete documents older than RETENTION_DAYS.

Policy is deployment-wide (not per-workspace) in this iteration.
Destructive sweeps must be explicitly enabled outside of dry-run.
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.config import Settings, get_settings
from app.db.models import AuditEvent, Document
from app.ingestion.service import delete_document
from app.storage.filesystem import StorageInterface

logger = logging.getLogger(__name__)


@dataclass(slots=True, frozen=True)
class RetentionCandidate:
    document_id: uuid.UUID
    workspace_id: uuid.UUID
    title: str
    created_at: datetime
    version_count: int


@dataclass(slots=True, frozen=True)
class RetentionSweepResult:
    dry_run: bool
    retention_days: int
    cutoff: datetime
    candidates: list[RetentionCandidate]
    deleted_ids: list[uuid.UUID]
    errors: list[str]


def find_expired_documents(
    session: Session,
    *,
    retention_days: int,
    now: datetime | None = None,
) -> list[RetentionCandidate]:
    if retention_days <= 0:
        return []
    cutoff = (now or datetime.now(UTC)) - timedelta(days=retention_days)
    rows = list(
        session.scalars(
            select(Document)
            .options(selectinload(Document.versions))
            .where(Document.created_at < cutoff)
            .order_by(Document.created_at.asc())
        ).all()
    )
    return [
        RetentionCandidate(
            document_id=doc.id,
            workspace_id=doc.workspace_id,
            title=doc.title,
            created_at=doc.created_at,
            version_count=len(doc.versions),
        )
        for doc in rows
    ]


def run_retention_sweep(
    session: Session,
    *,
    dry_run: bool = True,
    settings: Settings | None = None,
    storage: StorageInterface | None = None,
    now: datetime | None = None,
) -> RetentionSweepResult:
    cfg = settings or get_settings()
    candidates = find_expired_documents(
        session, retention_days=cfg.retention_days, now=now
    )
    cutoff = (now or datetime.now(UTC)) - timedelta(days=cfg.retention_days)
    deleted: list[uuid.UUID] = []
    errors: list[str] = []

    if dry_run:
        logger.info(
            "retention_dry_run",
            extra={"count": len(candidates), "retention_days": cfg.retention_days},
        )
        return RetentionSweepResult(
            dry_run=True,
            retention_days=cfg.retention_days,
            cutoff=cutoff,
            candidates=candidates,
            deleted_ids=[],
            errors=[],
        )

    for candidate in candidates:
        try:
            # Audit metadata only — never store title/body in detail for retention deletes.
            session.add(
                AuditEvent(
                    workspace_id=candidate.workspace_id,
                    action="retention.delete",
                    resource_type="document",
                    resource_id=str(candidate.document_id),
                    detail={
                        "retention_days": cfg.retention_days,
                        "created_at": candidate.created_at.isoformat(),
                        "version_count": candidate.version_count,
                    },
                )
            )
            session.flush()
            delete_document(
                session,
                candidate.document_id,
                settings=cfg,
                storage=storage,
            )
            deleted.append(candidate.document_id)
        except Exception as exc:  # noqa: BLE001
            logger.exception(
                "retention_delete_failed",
                extra={"document_id": str(candidate.document_id)},
            )
            errors.append(f"{candidate.document_id}: {exc}")

    logger.info(
        "retention_sweep_completed",
        extra={"deleted": len(deleted), "errors": len(errors), "dry_run": False},
    )
    return RetentionSweepResult(
        dry_run=False,
        retention_days=cfg.retention_days,
        cutoff=cutoff,
        candidates=candidates,
        deleted_ids=deleted,
        errors=errors,
    )
