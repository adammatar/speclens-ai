"""Rate limiting for sensitive POSTs.

Hosted/production uses Redis (shared across API instances).
Local/test falls back to in-process memory when Redis is unavailable.
"""

from __future__ import annotations

import hashlib
import logging
import time
from collections import defaultdict, deque
from threading import Lock
from typing import Any

from fastapi import HTTPException, Request, status

from app.core.config import get_settings

logger = logging.getLogger(__name__)

_lock = Lock()
_hits: dict[str, deque[float]] = defaultdict(deque)
_redis_client = None
_redis_failed = False


def _client_fingerprint(request: Request) -> str:
    """Stable fingerprint that does not embed the raw API token."""
    api_key = request.headers.get("X-API-Key") or request.headers.get("Authorization", "")
    if api_key:
        # Hash the credential material so Redis keys never store the token.
        digest = hashlib.sha256(api_key.encode("utf-8")).hexdigest()[:32]
        return f"key:{digest}"
    host = request.client.host if request.client else "unknown"
    return f"ip:{host}"


def _get_redis() -> Any:
    global _redis_client, _redis_failed
    if _redis_failed:
        return None
    if _redis_client is not None:
        return _redis_client
    settings = get_settings()
    try:
        import redis

        client = redis.Redis.from_url(settings.redis_url, decode_responses=True)
        client.ping()
        _redis_client = client
        return _redis_client
    except Exception as exc:  # noqa: BLE001
        logger.warning("rate_limit_redis_unavailable", extra={"error": str(exc)})
        _redis_failed = True
        return None


def _check_redis(bucket: str, fingerprint: str, limit: int) -> None:
    client: Any = _get_redis()
    if client is None:
        raise RuntimeError("redis unavailable")
    key = f"speclens:ratelimit:{bucket}:{fingerprint}"
    now = time.time()
    window_start = now - 60.0
    pipe = client.pipeline()
    pipe.zremrangebyscore(key, 0, window_start)
    pipe.zcard(key)
    pipe.zadd(key, {f"{now}:{id(fingerprint)}": now})
    pipe.expire(key, 120)
    results = pipe.execute()
    count = int(results[1])
    if count >= limit:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded",
        )


def _check_memory(bucket: str, fingerprint: str, limit: int) -> None:
    key = f"{bucket}:{fingerprint}"
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


def check_rate_limit(request: Request, bucket: str) -> None:
    settings = get_settings()
    limit = settings.rate_limit_per_minute
    if limit <= 0:
        return
    fingerprint = _client_fingerprint(request)
    hosted = settings.speclens_deployment_mode == "hosted" or settings.speclens_env == "production"
    if hosted:
        try:
            _check_redis(bucket, fingerprint, limit)
            return
        except HTTPException:
            raise
        except Exception as exc:  # noqa: BLE001
            # Hosted must not silently open the floodgates if Redis dies mid-flight.
            logger.error("rate_limit_redis_error", extra={"error": str(exc)})
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Rate limiter unavailable",
            ) from exc
    # Local/test: prefer Redis when available, else in-memory.
    try:
        _check_redis(bucket, fingerprint, limit)
    except HTTPException:
        raise
    except Exception:
        _check_memory(bucket, fingerprint, limit)


def reset_rate_limit_state_for_tests() -> None:
    """Clear in-memory buckets and redis client cache (tests only)."""
    global _redis_client, _redis_failed
    with _lock:
        _hits.clear()
    _redis_client = None
    _redis_failed = False
