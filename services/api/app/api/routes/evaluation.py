"""Authenticated evaluation report endpoint (no filesystem path in the browser)."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status

from app.security.auth import AuthContext, require_api_key

router = APIRouter(prefix="/evaluation", tags=["evaluation"])


def _candidate_paths() -> list[Path]:
    """Resolve report locations without leaking paths to clients."""
    override = os.getenv("SPECLENS_EVAL_REPORT_PATH", "").strip()
    if override:
        return [Path(override)]
    roots = [
        Path.cwd(),
        Path.cwd().parent.parent,  # /app when cwd is /app/services/api
        Path(__file__).resolve().parents[5],  # monorepo checkout
        Path("/workspace"),
        Path("/app"),
    ]
    paths: list[Path] = []
    seen: set[str] = set()
    for root in roots:
        for rel in (
            Path("artifacts") / "eval" / "report.json",
            Path("evals") / "reports" / "latest.json",
        ):
            candidate = (root / rel).resolve()
            key = str(candidate)
            if key not in seen:
                seen.add(key)
                paths.append(candidate)
    return paths


def _load_latest_report() -> dict[str, Any] | None:
    for path in _candidate_paths():
        if path.is_file():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            if isinstance(data, dict):
                return data
    return None


@router.get("/latest")
def get_latest_evaluation_report(
    _auth: AuthContext = Depends(require_api_key),
) -> dict[str, Any]:
    """Return the latest evaluation report for the dashboard UI."""
    report = _load_latest_report()
    if report is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No evaluation run available. Run `make eval` to generate a report.",
        )
    # Never expose filesystem paths or secrets.
    safe = dict(report)
    safe.pop("storage_root", None)
    safe["source"] = "speclens-eval-report"
    return safe
