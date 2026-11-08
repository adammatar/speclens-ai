"""chunk embeddings, FTS, and HNSW index

Revision ID: 20261108_0003
Revises: 20261108_0002
Create Date: 2026-11-08

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql

revision: str = "20261108_0003"
down_revision: str | None = "20261108_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.add_column("chunks", sa.Column("search_tsv", postgresql.TSVECTOR(), nullable=True))
    op.execute(
        """
        UPDATE chunks
        SET search_tsv = to_tsvector(
            'english',
            coalesce(text, '') || ' ' || coalesce(heading_path, '')
        )
        """
    )
    op.execute(
        """
        CREATE OR REPLACE FUNCTION speclens_chunks_search_tsv_trigger()
        RETURNS trigger AS $$
        BEGIN
          NEW.search_tsv := to_tsvector(
            'english',
            coalesce(NEW.text, '') || ' ' || coalesce(NEW.heading_path, '')
          );
          RETURN NEW;
        END
        $$ LANGUAGE plpgsql
        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_chunks_search_tsv
        BEFORE INSERT OR UPDATE OF text, heading_path ON chunks
        FOR EACH ROW
        EXECUTE FUNCTION speclens_chunks_search_tsv_trigger()
        """
    )
    op.create_index(
        "ix_chunks_search_tsv",
        "chunks",
        ["search_tsv"],
        postgresql_using="gin",
    )

    op.create_table(
        "chunk_embeddings",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("chunk_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("document_version_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("model_name", sa.String(length=128), nullable=False),
        sa.Column("dims", sa.Integer(), nullable=False),
        sa.Column("embedding", Vector(256), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["chunk_id"], ["chunks.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["document_version_id"],
            ["document_versions.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("chunk_id", "model_name", name="uq_chunk_embeddings_chunk_model"),
    )
    op.create_index("ix_chunk_embeddings_chunk_id", "chunk_embeddings", ["chunk_id"])
    op.create_index(
        "ix_chunk_embeddings_document_version_id",
        "chunk_embeddings",
        ["document_version_id"],
    )
    op.create_index("ix_chunk_embeddings_workspace_id", "chunk_embeddings", ["workspace_id"])
    op.execute(
        """
        CREATE INDEX ix_chunk_embeddings_hnsw
        ON chunk_embeddings
        USING hnsw (embedding vector_cosine_ops)
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_chunk_embeddings_hnsw")
    op.drop_index("ix_chunk_embeddings_workspace_id", table_name="chunk_embeddings")
    op.drop_index("ix_chunk_embeddings_document_version_id", table_name="chunk_embeddings")
    op.drop_index("ix_chunk_embeddings_chunk_id", table_name="chunk_embeddings")
    op.drop_table("chunk_embeddings")
    op.drop_index("ix_chunks_search_tsv", table_name="chunks")
    op.execute("DROP TRIGGER IF EXISTS trg_chunks_search_tsv ON chunks")
    op.execute("DROP FUNCTION IF EXISTS speclens_chunks_search_tsv_trigger")
    op.drop_column("chunks", "search_tsv")
