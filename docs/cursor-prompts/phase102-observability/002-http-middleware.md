# Phase 102 — HTTP Trace-ID Middleware

## File to create
`services/ui_iot/middleware/trace.py`

## Content

```python
"""
TraceMiddleware: generate or propagate X-Trace-ID per HTTP request.

- If the incoming request has an X-Trace-ID header, use it.
- Otherwise generate a new UUID4.
- Set trace_id_var context variable so JSON log lines carry the trace_id.
- Add X-Trace-ID to the response headers.
- Emit a structured access log line at the end of each request.
"""

import time
import uuid
import logging
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from shared.log import trace_id_var, get_logger

logger = get_logger("pulse.http")


class TraceMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        trace_id = request.headers.get("X-Trace-ID") or str(uuid.uuid4())
        token = trace_id_var.set(trace_id)
        t0 = time.monotonic()
        try:
            response: Response = await call_next(request)
        finally:
            elapsed_ms = round((time.monotonic() - t0) * 1000, 1)
            logger.info(
                "http_request",
                extra={
                    "method": request.method,
                    "path": request.url.path,
                    "status": getattr(response, "status_code", 0),
                    "elapsed_ms": elapsed_ms,
                },
            )
            trace_id_var.reset(token)
        response.headers["X-Trace-ID"] = trace_id
        return response
```

## Register middleware in services/ui_iot/app.py

After `app = FastAPI(...)` and before router registration:

```python
from middleware.trace import TraceMiddleware
app.add_middleware(TraceMiddleware)
```

## Ingest service (services/ingest_iot/ingest.py)

The ingest service uses raw MQTT callbacks, not HTTP middleware.
Assign a trace_id at the start of each message handler:

```python
import uuid
from shared.log import trace_id_var

async def _handle_message(client, topic, payload, qos, properties):
    token = trace_id_var.set(str(uuid.uuid4()))
    try:
        # ... existing handler logic ...
        pass
    finally:
        trace_id_var.reset(token)
```

Find the existing MQTT message callback in `ingest.py` and wrap its body
in the same try/finally pattern.
