# 005: Catch-All Exception Handler and Input Validation

## Context

The FastAPI app in `services/ui_iot/app.py` has two exception handlers:

1. **`HTTPException` handler** (lines 207-213): Redirects 401s for HTML clients, otherwise returns JSON `{"detail": ...}`.
2. **`RateLimitExceeded` handler** (lines 216-223): Returns 429 with `Retry-After`.

There is NO catch-all handler for unhandled exceptions. If an endpoint raises an unexpected `Exception` (e.g., `TypeError`, `KeyError`, database driver error), FastAPI/Starlette's default handler returns the **full stack trace** in the response body (in debug mode) or a generic 500 (in production mode). Neither includes a `trace_id` for log correlation.

Additionally, `services/shared/ingest_core.py` does not validate the length of metric keys in the telemetry payload. Extremely long keys (e.g., 10,000-char strings) could cause storage bloat, index issues, or unexpected errors in downstream processing.

## Step 1: Add Catch-All Exception Handler

### File: `services/ui_iot/app.py`

Add the catch-all handler after the existing `RateLimitExceeded` handler (after line 223).

The `TraceMiddleware` in `services/ui_iot/middleware/trace.py` (lines 18-41) sets `request.state.trace_id` on every request (line 22). The catch-all handler should extract this for the response.

**Important**: The handler must be registered for the base `Exception` class. Starlette processes exception handlers in specificity order -- `HTTPException` and `RateLimitExceeded` will still be caught by their specific handlers first. Only truly unhandled exceptions fall through to the base `Exception` handler.

```python
# Add after line 223 (after the rate_limit_handler):

@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    trace_id = getattr(request.state, "trace_id", None) or getattr(request.state, "request_id", None) or ""
    logger.error(
        "unhandled_exception",
        exc_info=exc,
        extra={
            "trace_id": trace_id,
            "method": request.method,
            "path": request.url.path,
            "exception_type": type(exc).__name__,
        },
    )
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error",
            "trace_id": trace_id,
        },
    )
```

This handler:
- Logs the full traceback via `exc_info=exc` -- the `JsonFormatter` in `shared/logging.py` (line 59-60) serializes `exc_info` into the `"exc"` JSON field.
- Extracts `trace_id` from `request.state.trace_id` (set by `TraceMiddleware` at `middleware/trace.py` line 22).
- Falls back to `request.state.request_id` (set by `RequestIdMiddleware` at `app.py` line 138) if trace_id is not set.
- Returns a generic 500 response with **no stack trace**, only the trace_id for log correlation.

**Verify the `logger` reference**: The `logger` is defined at `app.py` line 228: `logger = logging.getLogger(__name__)`. The handler must be placed after this line, or the logger must be moved above the handler. Since the handler is added after line 223 and the logger is at line 228, move the logger definition above the handler.

Alternatively, place the handler after line 228 (after the logger definition). The cleanest approach:

```python
# After line 223 (rate_limit_handler), and after line 228 (logger definition):
# Reorder so logger comes first:

pool: asyncpg.Pool | None = None
background_tasks: list[asyncio.Task] = []

logger = logging.getLogger(__name__)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    trace_id = getattr(request.state, "trace_id", None) or getattr(request.state, "request_id", None) or ""
    logger.error(
        "unhandled_exception",
        exc_info=exc,
        extra={
            "trace_id": trace_id,
            "method": request.method,
            "path": request.url.path,
            "exception_type": type(exc).__name__,
        },
    )
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error",
            "trace_id": trace_id,
        },
    )
```

Since `pool`, `background_tasks`, and `logger` are at lines 225-228 (right after the rate_limit_handler), and they are just variable declarations, the handler can go right after them:

Insert at **line 229** (after `logger = logging.getLogger(__name__)`):

```python
@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    trace_id = getattr(request.state, "trace_id", None) or getattr(request.state, "request_id", None) or ""
    logger.error(
        "unhandled_exception",
        exc_info=exc,
        extra={
            "trace_id": trace_id,
            "method": request.method,
            "path": request.url.path,
            "exception_type": type(exc).__name__,
        },
    )
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error",
            "trace_id": trace_id,
        },
    )
```

## Step 2: Add Metric Key Length Validation

### File: `services/shared/ingest_core.py`

The `validate_and_prepare()` function (lines 290-364) validates payload size and rate limits, but does not validate individual metric key lengths. A malicious or misconfigured device could send metric keys like `{"a"*10000: 42.0}` which would pass the payload size check (if under 8KB) but could cause issues in TimescaleDB JSONB indexing and downstream query patterns.

Add key validation inside `validate_and_prepare()`, after the payload size check (after line 314) and before the rate limiting logic (line 316):

```python
# AFTER line 314 (if payload_bytes > max_payload_bytes: return IngestResult(False, "PAYLOAD_TOO_LARGE")):

# Validate metric key lengths and count
MAX_METRIC_KEY_LENGTH = 128
MAX_METRIC_KEYS = 50
metrics = (payload or {}).get("metrics", {})
if isinstance(metrics, dict):
    if len(metrics) > MAX_METRIC_KEYS:
        return IngestResult(False, "TOO_MANY_METRICS")
    for key in metrics:
        if not isinstance(key, str) or len(key) > MAX_METRIC_KEY_LENGTH:
            return IngestResult(False, "METRIC_KEY_TOO_LONG")
        # Reject keys with control characters or null bytes
        if any(ord(c) < 32 for c in key):
            return IngestResult(False, "METRIC_KEY_INVALID")
```

Also add the constants near the top of the file, after line 14 (`SUPPORTED_ENVELOPE_VERSIONS = {"1"}`):

```python
MAX_METRIC_KEY_LENGTH = 128
MAX_METRIC_KEYS = 50
```

Update the status_map in `services/ui_iot/routes/ingest.py` (around line 199-208) to include the new rejection reasons:

```python
# Add to the status_map dict:
status_map = {
    "RATE_LIMITED": 429,
    "TOKEN_INVALID": 401,
    "TOKEN_MISSING": 401,
    "TOKEN_NOT_SET_IN_REGISTRY": 401,
    "DEVICE_REVOKED": 403,
    "UNREGISTERED_DEVICE": 403,
    "PAYLOAD_TOO_LARGE": 400,
    "SITE_MISMATCH": 400,
    "TOO_MANY_METRICS": 400,        # NEW
    "METRIC_KEY_TOO_LONG": 400,     # NEW
    "METRIC_KEY_INVALID": 400,      # NEW
}
```

## Step 3: Add Validation for Metric Key Patterns (Optional Hardening)

If you want stricter validation, add a regex check for metric key format. Metric keys should follow a pattern like `temp_c`, `battery_pct`, `rssi_dbm` -- alphanumeric with underscores and dots:

```python
import re

METRIC_KEY_PATTERN = re.compile(r'^[a-zA-Z][a-zA-Z0-9_./-]{0,127}$')

# In validate_and_prepare(), replace the key length check with:
for key in metrics:
    if not isinstance(key, str) or not METRIC_KEY_PATTERN.match(key):
        return IngestResult(False, "METRIC_KEY_INVALID")
```

This is optional -- the length check alone (Step 2) addresses the security concern. The regex adds defense against injection but may reject legitimate keys that use unusual characters.

## Verification

```bash
# 1. Test catch-all exception handler
# Create a temporary test endpoint that raises an unhandled exception:
# (Or trigger one by sending malformed data to an endpoint that doesn't handle it)

# Method: Send a request that triggers an unexpected error
# Example: POST to a JSON endpoint with invalid content-type
curl -v -X POST http://localhost:8080/customer/devices \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: text/plain" \
  -d "not json"
# Response should be 422 (Pydantic validation) or 500 with trace_id

# 2. Verify no stack trace in 500 response
# The response body should be:
# {"detail": "Internal server error", "trace_id": "abc123..."}
# NOT a Python traceback

# 3. Verify trace_id appears in logs
docker compose -f compose/docker-compose.yml logs ui --tail 20 | grep "unhandled_exception"
# Should show JSON log with trace_id, exception_type, and exc (traceback)

# 4. Test metric key validation
curl -X POST "http://localhost:8080/ingest/v1/tenant/test/device/test/telemetry" \
  -H "X-Provision-Token: test-token" \
  -H "Content-Type: application/json" \
  -d '{
    "site_id": "test-site",
    "seq": 1,
    "metrics": {"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa": 42.0}
  }'
# Expected: 400 METRIC_KEY_TOO_LONG (key is 133 chars, over 128 limit)

# 5. Test valid metric key
curl -X POST "http://localhost:8080/ingest/v1/tenant/test/device/test/telemetry" \
  -H "X-Provision-Token: test-token" \
  -H "Content-Type: application/json" \
  -d '{"site_id": "test-site", "seq": 1, "metrics": {"temp_c": 22.5}}'
# Expected: 202 (or auth error, but NOT METRIC_KEY_TOO_LONG)

# 6. Test too many metrics
python3 -c "
import json
metrics = {f'metric_{i}': i for i in range(55)}
payload = {'site_id': 'test', 'seq': 1, 'metrics': metrics}
print(json.dumps(payload))
" | curl -X POST "http://localhost:8080/ingest/v1/tenant/test/device/test/telemetry" \
  -H "X-Provision-Token: test-token" \
  -H "Content-Type: application/json" \
  -d @-
# Expected: 400 TOO_MANY_METRICS

# 7. Run tests
cd services/ui_iot && python -m pytest tests/ -x -q
cd services/shared && python -m pytest tests/ -x -q
```

## Notes

- The `@app.exception_handler(Exception)` in Starlette catches all exceptions that are NOT `HTTPException` or its subclasses. Since `RateLimitExceeded` is separately handled, and `HTTPException` has its own handler, only truly unhandled errors reach the catch-all.
- The `exc_info=exc` parameter to `logger.error()` causes Python's logging to include the full traceback in the log record, which the `JsonFormatter` serializes into the `"exc"` field of the JSON log line.
- The `trace_id` in the response allows operators to find the corresponding log entry by searching for that trace_id in the log aggregation system.
- The metric key validation runs on every ingest request. The checks are O(n) in the number of metric keys, which is bounded by `MAX_METRIC_KEYS=50` and typically under 20 in practice. Performance impact is negligible.
