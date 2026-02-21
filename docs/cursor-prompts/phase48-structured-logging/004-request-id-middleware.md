# Prompt 004 — Add `request_id` Middleware to ui_iot

## Context

Every HTTP request to `ui_iot` should get a unique `request_id` that appears in all log lines produced during that request. This makes it possible to trace a single request through the logs.

## Your Task

**Read `services/ui_iot/app.py` fully** before making changes.

### Step 1: Add `request_id` middleware

Add a middleware to `services/ui_iot/app.py` that:
1. Generates a `request_id` (UUID4, short form) for every incoming request
2. Accepts an `X-Request-ID` header from the client (if present, use it instead of generating)
3. Stores it in `request.state.request_id`
4. Adds it to the response headers as `X-Request-ID`
5. Logs the request start and end with timing

```python
import uuid
import time
from starlette.middleware.base import BaseHTTPMiddleware

class RequestIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())[:8]
        request.state.request_id = request_id
        start = time.monotonic()

        response = await call_next(request)

        duration_ms = int((time.monotonic() - start) * 1000)
        response.headers["X-Request-ID"] = request_id

        logger.info(
            "request",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "status": response.status_code,
                "duration_ms": duration_ms,
            }
        )
        return response
```

Register it:
```python
app.add_middleware(RequestIdMiddleware)
```

### Step 2: Call `configure_logging("ui_iot")` at startup

In `services/ui_iot/app.py`, add at the module level (before any logging occurs):
```python
from shared.logging import configure_logging
configure_logging("ui_iot")
```

This upgrades all existing `logger = logging.getLogger(...)` calls in ui_iot routes to use the JSON formatter automatically — no changes needed in the route files.

### Step 3: Add `request_id` to route-level log lines (optional but recommended)

In the customer and operator route handlers, the `request_id` is available via `request.state.request_id`. For the most important audit-worthy operations (rule create, integration create, device edit), add it to the log:

```python
logger.info("alert rule created", extra={
    "request_id": request.state.request_id,
    "tenant_id": tenant_id,
    "rule_id": str(rule.get("rule_id")),
})
```

Only add this to the ~5 most important mutating operations — not every GET endpoint.

## Acceptance Criteria

- [ ] Every HTTP response includes `X-Request-ID` header
- [ ] Every request logged with method, path, status, duration_ms, request_id
- [ ] `configure_logging("ui_iot")` called at startup
- [ ] Existing route-level logging still works (no broken imports)
- [ ] `pytest -m unit -v` passes
- [ ] `npm run build` clean (frontend unchanged)
