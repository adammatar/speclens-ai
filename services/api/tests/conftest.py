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
# Unit tests that do not seed API keys run with auth bypass.
os.environ.setdefault("AUTH_REQUIRED", "false")
os.environ.setdefault("RATE_LIMIT_PER_MINUTE", "0")


@pytest.fixture
def client() -> TestClient:
    from app.core.config import get_settings
    from app.main import create_app

    get_settings.cache_clear()
    with TestClient(create_app()) as test_client:
        yield test_client
    get_settings.cache_clear()
