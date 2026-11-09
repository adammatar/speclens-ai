"""requirement extraction jobs and requirements

Revision ID: 20261108_0005
Revises: 20261108_0004
Create Date: 2026-11-08

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20261108_0005"
down_revision: str | None = "20261108_0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    extraction_job_status = postgresql.ENUM(
        "queued",
        "running",
        "succeeded",
        "failed",
        name="extraction_job_status",
        create_type=False,
    )
    requirement_type = postgresql.ENUM(
        "functional",
        "non_functional",
        "constraint",
        "interface",
        "security",
        "performance",
        "compliance",
        "unknown",
        name="requirement_type",
        create_type=False,
    )
    requirement_priority = postgresql.ENUM(
        "must",
        "should",
        "could",
        "unknown",
        name="requirement_priority",
        create_type=False,
    )
    requirement_review_state = postgresql.ENUM(
        "proposed",
        "accepted",
        "edited",
        "rejected",
        name="requirement_review_state",
        create_type=False,
    )
    bind = op.get_bind()
    extraction_job_status.create(bind, checkfirst=True)
    requirement_type.create(bind, checkfirst=True)
    requirement_priority.create(bind, checkfirst=True)
    requirement_review_state.create(bind, checkfirst=True)

    op.create_table(
        "extraction_jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("document_version_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "status",
            postgresql.ENUM(
                "queued",
                "running",
                "succeeded",
                "failed",
                name="extraction_job_status",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("progress_pct", sa.Integer(), nullable=False),
        sa.Column("section_cursor", sa.Integer(), nullable=False),
        sa.Column("section_total", sa.Integer(), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("model_name", sa.String(length=128), nullable=True),
        sa.Column("prompt_version", sa.String(length=64), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["document_version_id"],
            ["document_versions.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_extraction_jobs_document_version_id",
        "extraction_jobs",
        ["document_version_id"],
    )
    op.create_index("ix_extraction_jobs_workspace_id", "extraction_jobs", ["workspace_id"])

    op.create_table(
        "requirements",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("document_version_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("extraction_job_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("section_path", sa.String(length=1024), nullable=False),
        sa.Column("external_id", sa.String(length=128), nullable=True),
        sa.Column(
            "requirement_type",
            postgresql.ENUM(
                "functional",
                "non_functional",
                "constraint",
                "interface",
                "security",
                "performance",
                "compliance",
                "unknown",
                name="requirement_type",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("statement", sa.Text(), nullable=False),
        sa.Column("rationale", sa.Text(), nullable=True),
        sa.Column(
            "priority",
            postgresql.ENUM(
                "must",
                "should",
                "could",
                "unknown",
                name="requirement_priority",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("acceptance_criteria", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("dependencies", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("ambiguities", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "contradiction_candidates",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("sources", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "review_state",
            postgresql.ENUM(
                "proposed",
                "accepted",
                "edited",
                "rejected",
                name="requirement_review_state",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("original_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("is_eval_example", sa.Boolean(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["document_version_id"],
            ["document_versions.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["extraction_job_id"],
            ["extraction_jobs.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_requirements_workspace_id", "requirements", ["workspace_id"])
    op.create_index("ix_requirements_document_id", "requirements", ["document_id"])
    op.create_index(
        "ix_requirements_document_version_id",
        "requirements",
        ["document_version_id"],
    )
    op.create_index(
        "ix_requirements_extraction_job_id",
        "requirements",
        ["extraction_job_id"],
    )
    op.create_index("ix_requirements_review_state", "requirements", ["review_state"])


def downgrade() -> None:
    op.drop_index("ix_requirements_review_state", table_name="requirements")
    op.drop_index("ix_requirements_extraction_job_id", table_name="requirements")
    op.drop_index("ix_requirements_document_version_id", table_name="requirements")
    op.drop_index("ix_requirements_document_id", table_name="requirements")
    op.drop_index("ix_requirements_workspace_id", table_name="requirements")
    op.drop_table("requirements")
    op.drop_index("ix_extraction_jobs_workspace_id", table_name="extraction_jobs")
    op.drop_index("ix_extraction_jobs_document_version_id", table_name="extraction_jobs")
    op.drop_table("extraction_jobs")
    bind = op.get_bind()
    postgresql.ENUM(name="requirement_review_state").drop(bind, checkfirst=True)
    postgresql.ENUM(name="requirement_priority").drop(bind, checkfirst=True)
    postgresql.ENUM(name="requirement_type").drop(bind, checkfirst=True)
    postgresql.ENUM(name="extraction_job_status").drop(bind, checkfirst=True)
