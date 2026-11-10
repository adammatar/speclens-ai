"""Request correlation ID middleware."""

from __future__ import annotations

import uuid

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

HEADER = "X-Request-ID"


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        incoming = request.headers.get(HEADER) or request.headers.get("X-Correlation-ID")
        request_id = incoming.strip() if incoming else str(uuid.uuid4())
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers[HEADER] = request_id
        return response
