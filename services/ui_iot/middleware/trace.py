"""
Trace middleware for request-scoped correlation IDs.
"""

import re
import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from shared.logging import trace_id_var
from shared.logging import get_logger
from shared.metrics import http_request_duration_seconds, http_requests_total

logger = get_logger("pulse.http")


# Regex to match UUIDs and numeric IDs in URL paths
_UUID_RE = re.compile(
    r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}"
)
_NUMERIC_ID_RE = re.compile(r"/\d+(?=/|$)")


def normalize_path(path: str) -> str:
    """
    Replace UUIDs and numeric IDs in URL paths with placeholders
    to prevent Prometheus label cardinality explosion.

    Examples:
        /customer/devices/abc123-def4-5678-9abc-def012345678/metrics
        -> /customer/devices/{id}/metrics

        /api/v2/alerts/42
        -> /api/v2/alerts/{id}
    """
    result = _UUID_RE.sub("{id}", path)
    result = _NUMERIC_ID_RE.sub("/{id}", result)
    return result


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
            elapsed = time.monotonic() - started
            elapsed_ms = round(elapsed * 1000, 1)
            status_code = getattr(response, "status_code", 500)
            method = request.method
            path_template = normalize_path(request.url.path)

            # Emit Prometheus metrics
            http_request_duration_seconds.labels(
                method=method,
                path_template=path_template,
                status_code=str(status_code),
            ).observe(elapsed)

            http_requests_total.labels(
                method=method,
                path_template=path_template,
                status_code=str(status_code),
            ).inc()

            logger.info(
                "http_request",
                extra={
                    "method": method,
                    "path": request.url.path,
                    "status": status_code,
                    "elapsed_ms": elapsed_ms,
                },
            )
            trace_id_var.reset(token)
            if response is not None:
                response.headers["X-Trace-ID"] = trace_id
