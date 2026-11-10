"""Evaluation report API tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
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
    with TestClient(create_app()) as test_client:
        yield test_client
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
    with TestClient(create_app()) as client:
        response = client.get("/api/v1/evaluation/latest")
        assert response.status_code == 404
    get_settings.cache_clear()
