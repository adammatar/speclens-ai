"""Health endpoint smoke tests."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError


def test_health_returns_ok(client: TestClient) -> None:
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_ready_fails_closed_when_db_unreachable(client: TestClient) -> None:
    with patch("app.api.routes.health.get_engine") as mock_engine:
        engine = MagicMock()
        engine.connect.side_effect = OperationalError(
            "SELECT 1",
            {},
            Exception("connection refused"),
        )
        mock_engine.return_value = engine
        response = client.get("/api/v1/ready")
    assert response.status_code == 503
    body = response.json()
    assert body["status"] == "unavailable"
    assert body["database"] == "down"


def test_ready_ok_when_db_reachable(client: TestClient) -> None:
    with patch("app.api.routes.health.get_engine") as mock_engine:
        conn = MagicMock()
        conn.__enter__.return_value = conn
        conn.__exit__.return_value = False
        conn.execute.return_value = None
        engine = MagicMock()
        engine.connect.return_value = conn
        mock_engine.return_value = engine
        response = client.get("/api/v1/ready")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["database"] == "up"
