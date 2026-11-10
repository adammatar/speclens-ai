"""API key lifecycle helpers (hash-at-rest; plaintext shown once)."""

from __future__ import annotations

import secrets
import uuid
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.db.models import ApiKey, User, Workspace, WorkspaceMembership, WorkspaceRole
from app.security.auth import hash_api_key

LOCAL_BOOTSTRAP_KEY = "speclens-local-dev-key"
DEFAULT_WORKSPACE_ID = uuid.UUID("00000000-0000-4000-8000-000000000001")
BOOTSTRAP_USER_ID = uuid.UUID("00000000-0000-4000-8000-000000000011")
BOOTSTRAP_KEY_ID = uuid.UUID("00000000-0000-4000-8000-000000000012")


@dataclass(slots=True, frozen=True)
class CreatedApiKey:
    key_id: uuid.UUID
    user_id: uuid.UUID
    email: str
    name: str
    key_prefix: str
    plaintext: str


def generate_api_key(*, prefix: str = "sl_") -> str:
    """High-entropy API key (urlsafe; ~256 bits of entropy with 32 bytes)."""
    return f"{prefix}{secrets.token_urlsafe(32)}"


def ensure_workspace(session: Session, workspace_id: uuid.UUID = DEFAULT_WORKSPACE_ID) -> Workspace:
    workspace = session.get(Workspace, workspace_id)
    if workspace is None:
        workspace = Workspace(id=workspace_id, name="default")
        session.add(workspace)
        session.flush()
    return workspace


def ensure_user(
    session: Session,
    *,
    email: str,
    display_name: str,
    user_id: uuid.UUID | None = None,
) -> User:
    user = session.scalar(select(User).where(User.email == email))
    if user is None:
        user = User(
            id=user_id or uuid.uuid4(),
            email=email,
            display_name=display_name,
            is_active=True,
        )
        session.add(user)
        session.flush()
    return user


def ensure_membership(
    session: Session,
    *,
    workspace_id: uuid.UUID,
    user_id: uuid.UUID,
    role: WorkspaceRole = WorkspaceRole.OWNER,
) -> WorkspaceMembership:
    existing = session.scalar(
        select(WorkspaceMembership).where(
            WorkspaceMembership.workspace_id == workspace_id,
            WorkspaceMembership.user_id == user_id,
        )
    )
    if existing is not None:
        return existing
    membership = WorkspaceMembership(
        workspace_id=workspace_id,
        user_id=user_id,
        role=role,
    )
    session.add(membership)
    session.flush()
    return membership


def create_api_key(
    session: Session,
    *,
    user: User,
    name: str,
    plaintext: str | None = None,
    key_id: uuid.UUID | None = None,
) -> CreatedApiKey:
    raw = plaintext or generate_api_key()
    if raw == LOCAL_BOOTSTRAP_KEY:
        raise ValueError(
            "Refusing known local bootstrap key; use bootstrap_local() for local/CI only"
        )
    digest = hash_api_key(raw)
    existing = session.scalar(select(ApiKey).where(ApiKey.key_hash == digest))
    if existing is not None:
        raise ValueError("API key hash already exists")
    row = ApiKey(
        id=key_id or uuid.uuid4(),
        user_id=user.id,
        name=name[:128],
        key_prefix=raw[:12],
        key_hash=digest,
        is_active=True,
    )
    session.add(row)
    session.flush()
    return CreatedApiKey(
        key_id=row.id,
        user_id=user.id,
        email=user.email,
        name=row.name,
        key_prefix=row.key_prefix,
        plaintext=raw,
    )


def list_api_keys(session: Session, *, user_id: uuid.UUID | None = None) -> list[ApiKey]:
    stmt = select(ApiKey).options(selectinload(ApiKey.user)).order_by(ApiKey.created_at.desc())
    if user_id is not None:
        stmt = stmt.where(ApiKey.user_id == user_id)
    return list(session.scalars(stmt).all())


def disable_api_key(session: Session, key_id: uuid.UUID) -> ApiKey:
    key = session.get(ApiKey, key_id)
    if key is None:
        raise LookupError(f"API key not found: {key_id}")
    key.is_active = False
    session.flush()
    return key


def rotate_api_key(session: Session, key_id: uuid.UUID) -> CreatedApiKey:
    old = session.get(ApiKey, key_id)
    if old is None:
        raise LookupError(f"API key not found: {key_id}")
    user = session.get(User, old.user_id)
    if user is None:
        raise LookupError("API key user missing")
    old.is_active = False
    session.flush()
    return create_api_key(session, user=user, name=f"{old.name}-rotated")


def bootstrap_local(session: Session) -> CreatedApiKey:
    """Idempotent local/CI bootstrap: owner user + known local key (never for production)."""
    ensure_workspace(session)
    user = ensure_user(
        session,
        email="local-admin@speclens.local",
        display_name="Local Admin",
        user_id=BOOTSTRAP_USER_ID,
    )
    ensure_membership(
        session,
        workspace_id=DEFAULT_WORKSPACE_ID,
        user_id=user.id,
        role=WorkspaceRole.OWNER,
    )
    digest = hash_api_key(LOCAL_BOOTSTRAP_KEY)
    existing = session.get(ApiKey, BOOTSTRAP_KEY_ID)
    if existing is None:
        # Insert directly — create_api_key() refuses the public bootstrap plaintext.
        existing = ApiKey(
            id=BOOTSTRAP_KEY_ID,
            user_id=user.id,
            name="local-bootstrap",
            key_prefix=LOCAL_BOOTSTRAP_KEY[:12],
            key_hash=digest,
            is_active=True,
        )
        session.add(existing)
        session.flush()
    else:
        existing.user_id = user.id
        existing.name = "local-bootstrap"
        existing.key_prefix = LOCAL_BOOTSTRAP_KEY[:12]
        existing.key_hash = digest
        existing.is_active = True
        existing.last_used_at = None
        session.flush()
    session.commit()
    return CreatedApiKey(
        key_id=existing.id,
        user_id=user.id,
        email=user.email,
        name=existing.name,
        key_prefix=existing.key_prefix,
        plaintext=LOCAL_BOOTSTRAP_KEY,
    )


def local_bootstrap_key_is_active(session: Session) -> bool:
    digest = hash_api_key(LOCAL_BOOTSTRAP_KEY)
    row = session.scalar(
        select(ApiKey).where(ApiKey.key_hash == digest, ApiKey.is_active.is_(True))
    )
    return row is not None
