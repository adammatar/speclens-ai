"""Content hashing helpers."""

from __future__ import annotations

import hashlib


def sha256_hex(data: bytes) -> str:
    """Return lowercase hex SHA-256 digest for deduplication."""
    return hashlib.sha256(data).hexdigest()
