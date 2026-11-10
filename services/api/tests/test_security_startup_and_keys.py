"""Production security startup + API key lifecycle tests."""

from __future__ import annotations

import os
import uuid
from unittest.mock import MagicMock

import pytest
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import Settings
from app.core.security_startup import SecurityStartupError, assert_safe_for_hosted
from app.ingestion.service import ensure_default_workspace
from app.security.auth import hash_api_key, require_api_key
from app.security.keys import (
    LOCAL_BOOTSTRAP_KEY,
    bootstrap_local,
    create_api_key,
    disable_api_key,
    generate_api_key,
    rotate_api_key,
)
from app.security.rate_limit import check_rate_limit, reset_rate_limit_state_for_tests

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg://speclens:speclens_dev_password@127.0.0.1:5432/speclens",
)


def _db_available(url: str) -> bool:
    try:
        engine = create_engine(url, pool_pre_ping=True)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        engine.dispose()
        return True
    except Exception:  # noqa: BLE001
        return False


pytestmark = pytest.mark.skipif(
    not _db_available(DATABASE_URL),
    reason="Postgres not available",
)


@pytest.fixture
def db_session() -> Session:
    engine = create_engine(DATABASE_URL, pool_pre_ping=True, future=True)
    from pgvector.psycopg import register_vector

    @event.listens_for(engine, "connect")
    def _register_vector(dbapi_connection: object, _connection_record: object) -> None:
        register_vector(dbapi_connection)

    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
    session = SessionLocal()
    ensure_default_workspace(session)
    session.commit()
    yield session
    session.close()
    engine.dispose()


def test_generate_api_key_high_entropy() -> None:
    a = generate_api_key()
    b = generate_api_key()
    assert a != b
    assert len(a) >= 40
    assert a.startswith("sl_")


def test_production_rejects_dev_password() -> None:
    settings = Settings(
        speclens_env="production",
        speclens_deployment_mode="hosted",
        auth_required=True,
        database_url="postgresql+psycopg://speclens:speclens_dev_password@postgres:5432/speclens",
    )
    with pytest.raises(SecurityStartupError, match="password"):
        assert_safe_for_hosted(settings, session=None)


def test_production_rejects_auth_required_false() -> None:
    settings = Settings(
        speclens_env="production",
        speclens_deployment_mode="hosted",
        auth_required=False,
        database_url="postgresql+psycopg://speclens:super-secret-prod-pass@postgres:5432/speclens",
    )
    with pytest.raises(SecurityStartupError, match="AUTH_REQUIRED"):
        assert_safe_for_hosted(settings, session=None)


def test_local_bootstrap_and_disable_rotate(db_session: Session) -> None:
    created = bootstrap_local(db_session)
    assert created.plaintext == LOCAL_BOOTSTRAP_KEY
    assert created.key_prefix == LOCAL_BOOTSTRAP_KEY[:12]

    # Only hash is stored
    from app.db.models import ApiKey

    row = db_session.get(ApiKey, created.key_id)
    assert row is not None
    assert row.key_hash == hash_api_key(LOCAL_BOOTSTRAP_KEY)
    assert LOCAL_BOOTSTRAP_KEY not in row.key_hash

    # Hosted check fails while bootstrap key active
    hosted = Settings(
        speclens_env="production",
        speclens_deployment_mode="hosted",
        auth_required=True,
        database_url="postgresql+psycopg://speclens:super-secret-prod-pass@postgres:5432/speclens",
    )
    with pytest.raises(SecurityStartupError, match="bootstrap"):
        assert_safe_for_hosted(hosted, db_session)

    disable_api_key(db_session, created.key_id)
    db_session.commit()
    assert_safe_for_hosted(hosted, db_session)  # passes once disabled

    # Create + rotate a normal key
    from app.security.keys import ensure_user

    user = ensure_user(
        db_session,
        email=f"owner-{uuid.uuid4().hex[:8]}@example.com",
        display_name="Owner",
    )
    first = create_api_key(db_session, user=user, name="primary")
    db_session.commit()
    rotated = rotate_api_key(db_session, first.key_id)
    db_session.commit()
    assert rotated.plaintext != first.plaintext
    old = db_session.get(ApiKey, first.key_id)
    assert old is not None and old.is_active is False


def test_disabled_key_returns_401(db_session: Session) -> None:
    from fastapi import HTTPException

    from app.security.keys import ensure_user

    user = ensure_user(db_session, email=f"u-{uuid.uuid4().hex[:8]}@example.com", display_name="U")
    created = create_api_key(db_session, user=user, name="tmp")
    db_session.commit()
    disable_api_key(db_session, created.key_id)
    db_session.commit()

    settings = Settings(auth_required=True, database_url=DATABASE_URL, speclens_env="test")
    with pytest.raises(HTTPException) as exc:
        require_api_key(
            session=db_session,
            settings=settings,
            authorization=f"Bearer {created.plaintext}",
            x_api_key=None,
        )
    assert exc.value.status_code == 401


def test_rate_limit_fingerprint_does_not_embed_raw_token() -> None:
    from fastapi import HTTPException

    reset_rate_limit_state_for_tests()
    request = MagicMock()
    request.client.host = "127.0.0.1"
    secret = "sl_" + ("a" * 40)
    request.headers.get = lambda key, default="": {
        "Authorization": f"Bearer {secret}",
        "X-API-Key": "",
    }.get(key, default)
    settings_patch = Settings(
        rate_limit_per_minute=3,
        speclens_deployment_mode="local",
        speclens_env="test",
        redis_url="redis://127.0.0.1:6379/15",
    )
    from unittest.mock import patch

    # Force memory limiter (simulate redis down for local).
    with (
        patch("app.security.rate_limit.get_settings", return_value=settings_patch),
        patch("app.security.rate_limit._get_redis", return_value=None),
        patch("app.security.rate_limit._check_redis", side_effect=RuntimeError("down")),
    ):
        for _ in range(3):
            check_rate_limit(request, "upload")
        with pytest.raises(HTTPException) as exc:
            check_rate_limit(request, "upload")
        assert exc.value.status_code == 429
    # Fingerprint must hash the credential, never embed the raw token.
    from app.security.rate_limit import _client_fingerprint

    fp = _client_fingerprint(request)
    assert secret not in fp
    assert fp.startswith("key:")


def test_redis_rate_limit_shared_across_instances() -> None:
    """Two limiter 'instances' (fresh client caches) share Redis counters."""
    from unittest.mock import patch

    import redis as redis_lib
    from fastapi import HTTPException

    redis_url = os.getenv("REDIS_URL", "redis://127.0.0.1:6379/0")
    try:
        client = redis_lib.Redis.from_url(redis_url, decode_responses=True)
        client.ping()
        # Isolate this test on a dedicated logical DB when possible.
        client.flushdb()
    except Exception:  # noqa: BLE001
        pytest.skip("Redis not available for shared rate-limit test")

    reset_rate_limit_state_for_tests()
    secret = "sl_" + ("b" * 40)
    request = MagicMock()
    request.client.host = "10.0.0.1"
    request.headers.get = lambda key, default="": {
        "Authorization": f"Bearer {secret}",
        "X-API-Key": "",
    }.get(key, default)

    settings_patch = Settings(
        rate_limit_per_minute=2,
        speclens_deployment_mode="hosted",
        speclens_env="production",
        redis_url=redis_url,
        auth_required=True,
        database_url="postgresql+psycopg://speclens:super-secret-prod-pass@postgres:5432/speclens",
    )

    with patch("app.security.rate_limit.get_settings", return_value=settings_patch):
        check_rate_limit(request, "qa-shared")
        # Simulate a second API process by clearing the cached redis client.
        reset_rate_limit_state_for_tests()
        check_rate_limit(request, "qa-shared")
        reset_rate_limit_state_for_tests()
        with pytest.raises(HTTPException) as exc:
            check_rate_limit(request, "qa-shared")
        assert exc.value.status_code == 429
