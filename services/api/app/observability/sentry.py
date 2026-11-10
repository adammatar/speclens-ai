"""Optional Sentry wiring with privacy redaction."""

from __future__ import annotations

import logging
import re
from typing import Any

logger = logging.getLogger(__name__)

_SECRET_RE = re.compile(
    r"(?i)(authorization|api[_-]?key|x-api-key|bearer\s+\S+|sk-[a-z0-9]+|"
    r"speclens-local-dev-key)"
)
_BODY_KEYS = frozenset(
    {
        "content",
        "text",
        "excerpt",
        "source_quote",
        "prompt",
        "question",
        "statement",
        "body",
        "file",
        "data",
    }
)


def _redact_value(value: Any) -> Any:
    if isinstance(value, str):
        if _SECRET_RE.search(value) or len(value) > 500:
            return "[REDACTED]"
        return value
    if isinstance(value, dict):
        out = {}
        for key, item in value.items():
            if str(key).lower() in _BODY_KEYS or _SECRET_RE.search(str(key)):
                out[key] = "[REDACTED]"
            else:
                out[key] = _redact_value(item)
        return out
    if isinstance(value, list):
        return [_redact_value(item) for item in value[:20]]
    return value


def before_send(
    event: dict[str, Any],
    _hint: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    """Strip document content, prompts, quotes, and credentials before export."""
    if "request" in event and isinstance(event["request"], dict):
        req = event["request"]
        headers = req.get("headers")
        if isinstance(headers, dict):
            req["headers"] = {
                k: ("[REDACTED]" if _SECRET_RE.search(str(k)) or _SECRET_RE.search(str(v)) else v)
                for k, v in headers.items()
            }
        if "data" in req:
            req["data"] = "[REDACTED]"
        if "cookies" in req:
            req["cookies"] = "[REDACTED]"
    if "extra" in event:
        event["extra"] = _redact_value(event["extra"])
    if "contexts" in event:
        event["contexts"] = _redact_value(event["contexts"])
    return event


def init_sentry(*, dsn: str, environment: str, service: str) -> bool:
    """Initialize Sentry when DSN is non-empty. Returns True if enabled."""
    if not dsn.strip():
        return False
    try:
        import sentry_sdk
        from sentry_sdk.integrations.celery import CeleryIntegration
        from sentry_sdk.integrations.fastapi import FastApiIntegration
        from sentry_sdk.integrations.logging import LoggingIntegration
    except ImportError:
        logger.warning("sentry_sdk_not_installed")
        return False

    integrations: list[Any] = [
        LoggingIntegration(level=logging.INFO, event_level=logging.ERROR),
    ]
    if service == "api":
        integrations.append(FastApiIntegration())
    if service == "worker":
        integrations.append(CeleryIntegration())

    sentry_sdk.init(
        dsn=dsn,
        environment=environment,
        send_default_pii=False,
        before_send=before_send,
        integrations=integrations,
        traces_sample_rate=0.0,
    )
    logger.info("sentry_initialized", extra={"service": service, "environment": environment})
    return True
