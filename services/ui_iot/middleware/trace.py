"""
Trace middleware for request-scoped correlation IDs.
"""

import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from shared.logging import trace_id_var
from shared.logging import get_logger

logger = get_logger("pulse.http")


class TraceMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        trace_id = request.headers.get("X-Trace-ID") or str(uuid.uuid4())
        token = trace_id_var.set(trace_id)
        request.state.trace_id = trace_id
        started = time.monotonic()
        response: Response | None = None
        try:
            response = await call_next(request)
            return response
        finally:
            elapsed_ms = round((time.monotonic() - started) * 1000, 1)
            logger.info(
                "http_request",
                extra={
                    "method": request.method,
                    "path": request.url.path,
                    "status": getattr(response, "status_code", 500),
                    "elapsed_ms": elapsed_ms,
                },
            )
            trace_id_var.reset(token)
            if response is not None:
                response.headers["X-Trace-ID"] = trace_id
