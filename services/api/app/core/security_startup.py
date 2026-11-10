"""Fail-fast production/hosted security checks."""

from __future__ import annotations

import logging
import re

from sqlalchemy.orm import Session

from app.core.config import Settings
from app.security.keys import LOCAL_BOOTSTRAP_KEY, local_bootstrap_key_is_active

logger = logging.getLogger(__name__)

KNOWN_INSECURE_PASSWORDS = frozenset(
    {
        "speclens_dev_password",
        "password",
        "postgres",
        "changeme",
    }
)


class SecurityStartupError(RuntimeError):
    """Raised when hosted/production configuration is unsafe."""


def _password_from_database_url(url: str) -> str | None:
    # postgresql+psycopg://user:pass@host/db
    match = re.search(r"://[^:]+:([^@]+)@", url)
    if not match:
        return None
    return match.group(1)


def assert_safe_for_hosted(settings: Settings, session: Session | None = None) -> None:
    """Refuse hosted/production boot with development credentials or auth disabled."""
    hosted = settings.speclens_deployment_mode == "hosted" or settings.speclens_env == "production"
    if not hosted:
        return

    errors: list[str] = []
    if not settings.auth_required:
        errors.append("AUTH_REQUIRED must be true in hosted/production mode")

    password = _password_from_database_url(settings.database_url)
    if password is None or password in KNOWN_INSECURE_PASSWORDS:
        errors.append(
            "DATABASE_URL must use a non-development password in hosted/production mode"
        )

    if session is not None and local_bootstrap_key_is_active(session):
        errors.append(
            f"Known local bootstrap API key ({LOCAL_BOOTSTRAP_KEY}) must not be active "
            "in hosted/production mode"
        )

    if errors:
        joined = "; ".join(errors)
        logger.error("security_startup_failed", extra={"errors": errors})
        raise SecurityStartupError(joined)


def validate_local_settings_ok(settings: Settings) -> None:
    """Local/test may use documented bootstrap materials; no-op guard for symmetry."""
    _ = settings
