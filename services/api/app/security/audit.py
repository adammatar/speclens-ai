"""Audit event writer (never stores raw document bodies)."""

from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from app.db.models import AuditEvent
from app.security.auth import AuthContext
from app.security.redaction import redact_mapping


def record_audit(
    session: Session,
    *,
    auth: AuthContext | None,
    action: str,
    workspace_id: uuid.UUID | None = None,
    resource_type: str | None = None,
    resource_id: str | uuid.UUID | None = None,
    detail: dict[str, object] | None = None,
) -> None:
    event = AuditEvent(
        workspace_id=workspace_id,
        user_id=auth.user_id if auth else None,
        action=action,
        resource_type=resource_type,
        resource_id=str(resource_id) if resource_id is not None else None,
        detail=redact_mapping(detail) if detail else None,
    )
    session.add(event)
    session.commit()
