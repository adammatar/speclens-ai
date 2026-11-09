"""API key authentication."""

from __future__ import annotations

import hashlib
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.config import Settings, get_settings
from app.db.models import ApiKey, User, WorkspaceRole
from app.db.session import get_session


@dataclass(slots=True)
class AuthContext:
    user_id: uuid.UUID
    email: str
    api_key_id: uuid.UUID
    memberships: dict[uuid.UUID, WorkspaceRole] = field(default_factory=dict)

    def role_for(self, workspace_id: uuid.UUID) -> WorkspaceRole | None:
        return self.memberships.get(workspace_id)

    @property
    def workspace_ids(self) -> set[uuid.UUID]:
        return set(self.memberships.keys())


def hash_api_key(raw_key: str) -> str:
    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()


def _extract_raw_key(
    authorization: str | None,
    x_api_key: str | None,
) -> str | None:
    if x_api_key and x_api_key.strip():
        return x_api_key.strip()
    if authorization:
        parts = authorization.split(None, 1)
        if len(parts) == 2 and parts[0].lower() == "bearer" and parts[1].strip():
            return parts[1].strip()
    return None


def require_api_key(
    session: Session = Depends(get_session),
    settings: Settings = Depends(get_settings),
    authorization: str | None = Header(default=None),
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
) -> AuthContext:
    if not settings.auth_required:
        # Test-only bypass: still bind bootstrap user if present.
        return _anonymous_or_bootstrap(session)

    raw = _extract_raw_key(authorization, x_api_key)
    if not raw:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API key",
            headers={"WWW-Authenticate": "Bearer"},
        )
    digest = hash_api_key(raw)
    api_key = session.scalar(
        select(ApiKey)
        .where(ApiKey.key_hash == digest, ApiKey.is_active.is_(True))
        .options(
            selectinload(ApiKey.user).selectinload(User.memberships),
        )
    )
    if api_key is None or api_key.user is None or not api_key.user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
            headers={"WWW-Authenticate": "Bearer"},
        )
    api_key.last_used_at = datetime.now(UTC)
    session.commit()
    memberships = {
        membership.workspace_id: membership.role for membership in api_key.user.memberships
    }
    return AuthContext(
        user_id=api_key.user_id,
        email=api_key.user.email,
        api_key_id=api_key.id,
        memberships=memberships,
    )


def _anonymous_or_bootstrap(session: Session) -> AuthContext:
    """Used when auth_required=false (unit tests without seeded keys)."""
    user = session.scalar(select(User).where(User.email == "local-admin@speclens.local"))
    if user is None:
        return AuthContext(
            user_id=uuid.UUID("00000000-0000-4000-8000-000000000099"),
            email="test@speclens.local",
            api_key_id=uuid.UUID("00000000-0000-4000-8000-000000000098"),
            memberships={uuid.UUID("00000000-0000-4000-8000-000000000001"): WorkspaceRole.OWNER},
        )
    memberships = {m.workspace_id: m.role for m in user.memberships}
    key = session.scalar(select(ApiKey).where(ApiKey.user_id == user.id))
    return AuthContext(
        user_id=user.id,
        email=user.email,
        api_key_id=key.id if key else uuid.uuid4(),
        memberships=memberships,
    )
