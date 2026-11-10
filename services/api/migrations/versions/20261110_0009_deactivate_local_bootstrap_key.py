"""Deactivate the publicly known local bootstrap API key.

Schema from 20261108_0007 remains; local/CI re-activate via `python -m app.cli bootstrap-local`.
Production must never run bootstrap-local.

Revision ID: 20261110_0009
Revises: 20261109_0008
Create Date: 2026-11-10

"""

from __future__ import annotations

import uuid
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20261110_0009"
down_revision: str | None = "20261109_0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

BOOTSTRAP_KEY_ID = uuid.UUID("00000000-0000-4000-8000-000000000012")


def upgrade() -> None:
    op.execute(
        sa.text("UPDATE api_keys SET is_active = false WHERE id = :id").bindparams(
            id=BOOTSTRAP_KEY_ID
        )
    )


def downgrade() -> None:
    # Do not re-enable a known public key automatically.
    pass
