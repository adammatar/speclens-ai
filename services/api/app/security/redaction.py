"""Log and payload redaction helpers."""

from __future__ import annotations

import re
from typing import Any

_SECRET_KEYS = {
    "authorization",
    "api_key",
    "apikey",
    "openai_api_key",
    "token",
    "password",
    "secret",
    "key_hash",
}
_BEARER_RE = re.compile(r"(Bearer\s+)(\S+)", re.IGNORECASE)


def redact_string(value: str) -> str:
    text = _BEARER_RE.sub(r"\1[REDACTED]", value)
    # Avoid redacting UUIDs (36 chars with hyphens) - focus on raw keys/hashes.
    if "speclens-local-dev-key" in text:
        text = text.replace("speclens-local-dev-key", "[REDACTED]")
    return text


def redact_mapping(data: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in data.items():
        lowered = key.lower()
        if lowered in _SECRET_KEYS or "api_key" in lowered or lowered.endswith("_key"):
            out[key] = "[REDACTED]"
        elif isinstance(value, dict):
            out[key] = redact_mapping(value)
        elif isinstance(value, str):
            # Never log raw document bodies in structured extras.
            if lowered in {"text", "content", "excerpt", "prompt", "document_body", "source_quote"}:
                out[key] = f"[REDACTED len={len(value)}]"
            else:
                out[key] = redact_string(value)
        else:
            out[key] = value
    return out


def contains_forbidden_log_content(message: str) -> bool:
    """Heuristic used in tests: raw bootstrap key must never appear."""
    return "speclens-local-dev-key" in message
