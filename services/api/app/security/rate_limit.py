"""Simple in-process rate limiter for sensitive POSTs."""

from __future__ import annotations

import time
from collections import defaultdict, deque
from threading import Lock

from fastapi import HTTPException, Request, status

from app.core.config import get_settings

_lock = Lock()
_hits: dict[str, deque[float]] = defaultdict(deque)


def check_rate_limit(request: Request, bucket: str) -> None:
    settings = get_settings()
    limit = settings.rate_limit_per_minute
    if limit <= 0:
        return
    key = f"{bucket}:{request.client.host if request.client else 'unknown'}"
    # Prefer API key prefix from header without logging the secret.
    api_key = request.headers.get("X-API-Key") or request.headers.get("Authorization", "")
    if api_key:
        key = f"{bucket}:{hash(api_key) & 0xFFFFFFFF}"
    now = time.monotonic()
    window = 60.0
    with _lock:
        q = _hits[key]
        while q and now - q[0] > window:
            q.popleft()
        if len(q) >= limit:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded",
            )
        q.append(now)
