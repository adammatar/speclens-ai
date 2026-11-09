"""version comparison and requirement traceability

Revision ID: 20261108_0006
Revises: 20261108_0005
Create Date: 2026-11-08

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20261108_0006"
down_revision: str | None = "20261108_0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    comparison_job_status = postgresql.ENUM(
        "queued",
        "running",
        "succeeded",
        "failed",
        name="comparison_job_status",
        create_type=False,
    )
    change_category = postgresql.ENUM(
        "added",
        "removed",
        "clarified",
        "behavior_changed",
        "priority_changed",
        "acceptance_criteria_changed",
        "potential_breaking_change",
        "uncertain",
        name="change_category",
        create_type=False,
    )
    change_decision = postgresql.ENUM(
        "pending",
        "confirmed",
        "rejected",
        name="change_decision",
        create_type=False,
    )
    bind = op.get_bind()
    comparison_job_status.create(bind, checkfirst=True)
    change_category.create(bind, checkfirst=True)
    change_decision.create(bind, checkfirst=True)

    op.add_column("requirements", sa.Column("jira_ticket_id", sa.String(length=128), nullable=True))
    op.add_column("requirements", sa.Column("source_file", sa.String(length=1024), nullable=True))
    op.add_column("requirements", sa.Column("test_case_id", sa.String(length=256), nullable=True))
    op.add_column("requirements", sa.Column("implementation_note", sa.Text(), nullable=True))

    op.create_table(
        "comparison_jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("base_document_version_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("target_document_version_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "status",
            postgresql.ENUM(
                "queued",
                "running",
                "succeeded",
                "failed",
                name="comparison_job_status",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("progress_pct", sa.Integer(), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("change_count", sa.Integer(), nullable=False),
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
            ["base_document_version_id"],
            ["document_versions.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["target_document_version_id"],
            ["document_versions.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_comparison_jobs_workspace_id", "comparison_jobs", ["workspace_id"])
    op.create_index(
        "ix_comparison_jobs_base_document_version_id",
        "comparison_jobs",
        ["base_document_version_id"],
    )
    op.create_index(
        "ix_comparison_jobs_target_document_version_id",
        "comparison_jobs",
        ["target_document_version_id"],
    )

    op.create_table(
        "requirement_changes",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("comparison_job_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "category",
            postgresql.ENUM(
                "added",
                "removed",
                "clarified",
                "behavior_changed",
                "priority_changed",
                "acceptance_criteria_changed",
                "potential_breaking_change",
                "uncertain",
                name="change_category",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("base_requirement_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("target_requirement_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("similarity", sa.Float(), nullable=True),
        sa.Column("old_statement", sa.Text(), nullable=True),
        sa.Column("new_statement", sa.Text(), nullable=True),
        sa.Column("old_source_quote", sa.Text(), nullable=True),
        sa.Column("new_source_quote", sa.Text(), nullable=True),
        sa.Column(
            "decision",
            postgresql.ENUM(
                "pending",
                "confirmed",
                "rejected",
                name="change_decision",
                create_type=False,
            ),
            nullable=False,
        ),
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
        sa.ForeignKeyConstraint(
            ["base_requirement_id"],
            ["requirements.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["comparison_job_id"],
            ["comparison_jobs.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["target_requirement_id"],
            ["requirements.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_requirement_changes_comparison_job_id",
        "requirement_changes",
        ["comparison_job_id"],
    )
    op.create_index(
        "ix_requirement_changes_base_requirement_id",
        "requirement_changes",
        ["base_requirement_id"],
    )
    op.create_index(
        "ix_requirement_changes_target_requirement_id",
        "requirement_changes",
        ["target_requirement_id"],
    )
    op.create_index("ix_requirement_changes_decision", "requirement_changes", ["decision"])


def downgrade() -> None:
    op.drop_index("ix_requirement_changes_decision", table_name="requirement_changes")
    op.drop_index(
        "ix_requirement_changes_target_requirement_id",
        table_name="requirement_changes",
    )
    op.drop_index(
        "ix_requirement_changes_base_requirement_id",
        table_name="requirement_changes",
    )
    op.drop_index(
        "ix_requirement_changes_comparison_job_id",
        table_name="requirement_changes",
    )
    op.drop_table("requirement_changes")
    op.drop_index(
        "ix_comparison_jobs_target_document_version_id",
        table_name="comparison_jobs",
    )
    op.drop_index(
        "ix_comparison_jobs_base_document_version_id",
        table_name="comparison_jobs",
    )
    op.drop_index("ix_comparison_jobs_workspace_id", table_name="comparison_jobs")
    op.drop_table("comparison_jobs")
    op.drop_column("requirements", "implementation_note")
    op.drop_column("requirements", "test_case_id")
    op.drop_column("requirements", "source_file")
    op.drop_column("requirements", "jira_ticket_id")
    bind = op.get_bind()
    postgresql.ENUM(name="change_decision").drop(bind, checkfirst=True)
    postgresql.ENUM(name="change_category").drop(bind, checkfirst=True)
    postgresql.ENUM(name="comparison_job_status").drop(bind, checkfirst=True)
