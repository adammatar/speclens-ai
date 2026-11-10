"""Evaluation report API tests (no Postgres required)."""

from __future__ import annotations

import json
import uuid
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.db.models import WorkspaceRole
from app.security.auth import AuthContext, require_api_key


def _fake_auth() -> AuthContext:
    return AuthContext(
        user_id=uuid.UUID("00000000-0000-4000-8000-000000000099"),
        email="test@speclens.local",
        api_key_id=uuid.UUID("00000000-0000-4000-8000-000000000098"),
        memberships={
            uuid.UUID("00000000-0000-4000-8000-000000000001"): WorkspaceRole.OWNER,
        },
    )


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    report = {
        "mode": "stub",
        "synthetic_stub_badge": True,
        "metrics": {"retrieval_recall_at_10": 1.0},
        "generated_at": "2026-11-10T00:00:00+00:00",
    }
    path = tmp_path / "report.json"
    path.write_text(json.dumps(report), encoding="utf-8")
    monkeypatch.setenv("SPECLENS_EVAL_REPORT_PATH", str(path))
    monkeypatch.setenv("AUTH_REQUIRED", "false")
    monkeypatch.setenv("RATE_LIMIT_PER_MINUTE", "0")
    from app.core.config import get_settings
    from app.main import create_app

    get_settings.cache_clear()
    app = create_app()
    # File-based endpoint tests must not require Postgres for auth bypass lookups.
    app.dependency_overrides[require_api_key] = _fake_auth
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
    get_settings.cache_clear()


def test_latest_evaluation_report(client: TestClient) -> None:
    response = client.get("/api/v1/evaluation/latest")
    assert response.status_code == 200
    body = response.json()
    assert body["mode"] == "stub"
    assert body["synthetic_stub_badge"] is True
    assert body["source"] == "speclens-eval-report"
    assert "storage_root" not in body


def test_missing_evaluation_report(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("SPECLENS_EVAL_REPORT_PATH", str(tmp_path / "missing.json"))
    monkeypatch.setenv("AUTH_REQUIRED", "false")
    monkeypatch.setenv("RATE_LIMIT_PER_MINUTE", "0")
    from app.core.config import get_settings
    from app.main import create_app

    get_settings.cache_clear()
    app = create_app()
    app.dependency_overrides[require_api_key] = _fake_auth
    with TestClient(app) as client:
        response = client.get("/api/v1/evaluation/latest")
        assert response.status_code == 404
    app.dependency_overrides.clear()
    get_settings.cache_clear()
