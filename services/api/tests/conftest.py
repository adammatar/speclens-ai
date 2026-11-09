"""Shared pytest fixtures."""

from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient

# Force test settings before app import side effects.
os.environ.setdefault("SPECLENS_ENV", "test")
os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+psycopg://speclens:speclens_dev_password@localhost:5432/speclens",
)


@pytest.fixture
def client() -> TestClient:
    from app.main import create_app

    with TestClient(create_app()) as test_client:
        yield test_client
