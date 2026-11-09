"""security auth users memberships api keys audit

Revision ID: 20261108_0007
Revises: 20261108_0006
Create Date: 2026-11-09

"""

from __future__ import annotations

import hashlib
import uuid
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20261108_0007"
down_revision: str | None = "20261108_0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

DEFAULT_WORKSPACE_ID = uuid.UUID("00000000-0000-4000-8000-000000000001")
BOOTSTRAP_USER_ID = uuid.UUID("00000000-0000-4000-8000-000000000011")
BOOTSTRAP_KEY_ID = uuid.UUID("00000000-0000-4000-8000-000000000012")
# Local/CI only; plaintext documented in .env.example - never a production secret.
BOOTSTRAP_API_KEY = "speclens-local-dev-key"


def upgrade() -> None:
    workspace_role = postgresql.ENUM(
        "owner",
        "editor",
        "viewer",
        name="workspace_role",
        create_type=False,
    )
    workspace_role.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("display_name", sa.String(length=256), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
    )

    op.create_table(
        "workspace_memberships",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "role",
            postgresql.ENUM(
                "owner",
                "editor",
                "viewer",
                name="workspace_role",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("workspace_id", "user_id", name="uq_workspace_memberships_ws_user"),
    )
    op.create_index(
        "ix_workspace_memberships_workspace_id",
        "workspace_memberships",
        ["workspace_id"],
    )
    op.create_index("ix_workspace_memberships_user_id", "workspace_memberships", ["user_id"])

    op.create_table(
        "api_keys",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("key_prefix", sa.String(length=16), nullable=False),
        sa.Column("key_hash", sa.String(length=64), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("key_hash"),
    )
    op.create_index("ix_api_keys_user_id", "api_keys", ["user_id"])

    op.create_table(
        "audit_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("action", sa.String(length=128), nullable=False),
        sa.Column("resource_type", sa.String(length=64), nullable=True),
        sa.Column("resource_id", sa.String(length=64), nullable=True),
        sa.Column("detail", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_audit_events_workspace_id", "audit_events", ["workspace_id"])
    op.create_index("ix_audit_events_user_id", "audit_events", ["user_id"])
    op.create_index("ix_audit_events_action", "audit_events", ["action"])

    # Ensure default workspace exists, then bootstrap local owner + API key.
    op.execute(
        sa.text(
            "INSERT INTO workspaces (id, name) VALUES (:id, 'default') ON CONFLICT (id) DO NOTHING"
        ).bindparams(id=DEFAULT_WORKSPACE_ID)
    )
    key_hash = hashlib.sha256(BOOTSTRAP_API_KEY.encode("utf-8")).hexdigest()
    op.execute(
        sa.text(
            "INSERT INTO users (id, email, display_name, is_active) "
            "VALUES (:id, :email, :name, true) ON CONFLICT (id) DO NOTHING"
        ).bindparams(
            id=BOOTSTRAP_USER_ID,
            email="local-admin@speclens.local",
            name="Local Admin",
        )
    )
    op.execute(
        sa.text(
            "INSERT INTO workspace_memberships (id, workspace_id, user_id, role) "
            "VALUES (:id, :ws, :user, 'owner') "
            "ON CONFLICT ON CONSTRAINT uq_workspace_memberships_ws_user DO NOTHING"
        ).bindparams(
            id=uuid.uuid4(),
            ws=DEFAULT_WORKSPACE_ID,
            user=BOOTSTRAP_USER_ID,
        )
    )
    op.execute(
        sa.text(
            "INSERT INTO api_keys (id, user_id, name, key_prefix, key_hash, is_active) "
            "VALUES (:id, :user, 'local-bootstrap', :prefix, :hash, true) "
            "ON CONFLICT (id) DO NOTHING"
        ).bindparams(
            id=BOOTSTRAP_KEY_ID,
            user=BOOTSTRAP_USER_ID,
            prefix=BOOTSTRAP_API_KEY[:12],
            hash=key_hash,
        )
    )


def downgrade() -> None:
    op.drop_index("ix_audit_events_action", table_name="audit_events")
    op.drop_index("ix_audit_events_user_id", table_name="audit_events")
    op.drop_index("ix_audit_events_workspace_id", table_name="audit_events")
    op.drop_table("audit_events")
    op.drop_index("ix_api_keys_user_id", table_name="api_keys")
    op.drop_table("api_keys")
    op.drop_index("ix_workspace_memberships_user_id", table_name="workspace_memberships")
    op.drop_index("ix_workspace_memberships_workspace_id", table_name="workspace_memberships")
    op.drop_table("workspace_memberships")
    op.drop_table("users")
    postgresql.ENUM(name="workspace_role").drop(op.get_bind(), checkfirst=True)
