#!/usr/bin/env python3
"""Export accepted is_eval_example rows from the DB into evals/datasets/gold_import.jsonl.

Optional Phase 7 hook. Requires DATABASE_URL and a migrated database.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "evals" / "datasets" / "gold_import.jsonl"


def main() -> int:
    url = os.getenv("DATABASE_URL")
    if not url:
        print("DATABASE_URL not set; skipping gold import", file=sys.stderr)
        return 0

    sys.path.insert(0, str(ROOT / "services" / "api"))
    from sqlalchemy import create_engine, select
    from sqlalchemy.orm import Session, sessionmaker

    from app.db.models import Requirement, RequirementChange

    engine = create_engine(url, pool_pre_ping=True)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    session: Session = SessionLocal()
    rows: list[dict[str, object]] = []
    try:
        for req in session.scalars(
            select(Requirement).where(Requirement.is_eval_example.is_(True))
        ):
            rows.append(
                {
                    "kind": "requirement",
                    "id": str(req.id),
                    "statement": req.statement,
                    "original_payload": req.original_payload,
                    "review_state": req.review_state.value,
                }
            )
        for change in session.scalars(
            select(RequirementChange).where(RequirementChange.is_eval_example.is_(True))
        ):
            rows.append(
                {
                    "kind": "requirement_change",
                    "id": str(change.id),
                    "category": change.category.value,
                    "decision": change.decision.value,
                    "old_statement": change.old_statement,
                    "new_statement": change.new_statement,
                }
            )
    finally:
        session.close()
        engine.dispose()

    OUT.write_text(
        "\n".join(json.dumps(row, sort_keys=True) for row in rows) + ("\n" if rows else ""),
        encoding="utf-8",
    )
    print(f"Wrote {len(rows)} gold examples to {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
