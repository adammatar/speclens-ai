"""Switch chunk FTS from english to simple for multilingual (Hebrew) lexical search.

Revision ID: 20261109_0008
Revises: 20261108_0007
Create Date: 2026-11-09

"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "20261109_0008"
down_revision: str | None = "20261108_0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        CREATE OR REPLACE FUNCTION speclens_chunks_search_tsv_trigger()
        RETURNS trigger AS $$
        BEGIN
          NEW.search_tsv := to_tsvector(
            'simple',
            coalesce(NEW.text, '') || ' ' || coalesce(NEW.heading_path, '')
          );
          RETURN NEW;
        END
        $$ LANGUAGE plpgsql
        """
    )
    op.execute(
        """
        UPDATE chunks
        SET search_tsv = to_tsvector(
            'simple',
            coalesce(text, '') || ' ' || coalesce(heading_path, '')
        )
        """
    )


def downgrade() -> None:
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
        UPDATE chunks
        SET search_tsv = to_tsvector(
            'english',
            coalesce(text, '') || ' ' || coalesce(heading_path, '')
        )
        """
    )
