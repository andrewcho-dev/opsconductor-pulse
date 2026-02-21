# Task 002 -- Prometheus HTTP Metrics

## Commit Message

```
feat(metrics): add HTTP request histograms and auth failure counters
```

## Objective

Add Prometheus `Histogram` for HTTP request durations, `Counter` for HTTP request totals, and `Counter` for auth failures. Instrument `TraceMiddleware` to emit these metrics on every request. Increment the auth failure counter in the auth middleware.

## Files to Modify

1. `services/shared/metrics.py`
2. `services/ui_iot/middleware/trace.py`
3. `services/ui_iot/middleware/auth.py`

---

## Step 1: Add new Prometheus metrics to shared/metrics.py

**File**: `services/shared/metrics.py`

Add these imports and metric definitions after the existing metrics (after line 57, after `delivery_jobs_failed_total`):

```python
from prometheus_client import Counter, Gauge, Histogram
```

Update the existing import line at the top (line 8) to include `Histogram`:

```python
from prometheus_client import Counter, Gauge, Histogram
```

Then add these new metrics at the bottom of the file:

```python
# HTTP request metrics
http_request_duration_seconds = Histogram(
    "pulse_http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "path_template", "status_code"],
    buckets=[0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
)

http_requests_total = Counter(
    "pulse_http_requests_total",
    "Total HTTP requests",
    ["method", "path_template", "status_code"],
)

# Auth failure metrics
pulse_auth_failures_total = Counter(
    "pulse_auth_failures_total",
    "Total authentication failures by reason",
    ["reason"],
)
```

---

## Step 2: Add path normalization helper to trace.py

**File**: `services/ui_iot/middleware/trace.py`

This is critical to prevent cardinality explosion. Without normalization, each unique UUID in a path creates a unique label value, which can cause Prometheus OOM.

### 2a: Add imports

At the top of the file, add:

```python
import re
```

### 2b: Add path normalization function

Add this function before the `TraceMiddleware` class (before line 18):

```python
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
```

### 2c: Instrument TraceMiddleware dispatch method

Import the new metrics at the top of the file:

```python
from shared.metrics import http_request_duration_seconds, http_requests_total
```

Modify the `dispatch` method of `TraceMiddleware` to emit Prometheus metrics. The current method:

```python
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
```

Replace the `finally` block with:

```python
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
```

### Important: the `status_code` label must be a string

Prometheus labels are always strings. Use `str(status_code)` when calling `.labels()`.

---

## Step 3: Increment auth failure counter in auth.py

**File**: `services/ui_iot/middleware/auth.py`

### 3a: Import the new counter

Add to the imports at the top:

```python
from shared.metrics import pulse_auth_failures_total
```

### 3b: Increment counter on each failure

In the `JWTBearer.__call__` method (modified in task 001), add counter increments alongside the audit logging. Wherever `audit.auth_failure(reason=..., ...)` is called, also call:

```python
pulse_auth_failures_total.labels(reason=reason).inc()
```

Specifically, there are two places in `__call__` where `auth_failure` is called:

**Place 1**: Missing token case (around the `if not token:` block):

```python
if not token:
    audit = get_audit_logger()
    if audit:
        audit.auth_failure(reason="missing_token", ip_address=client_ip)
    pulse_auth_failures_total.labels(reason="missing_token").inc()
    raise HTTPException(status_code=401, detail="Missing authorization")
```

**Place 2**: Token validation failure (the `except HTTPException` block):

```python
except HTTPException as exc:
    audit = get_audit_logger()
    if audit:
        reason_map = {
            "Token expired": "expired",
            "Invalid token claims": "invalid_claims",
            "Invalid token": "invalid_token",
            "Unknown signing key": "unknown_key",
            "Auth service unavailable": "auth_unavailable",
        }
        reason = reason_map.get(exc.detail, "unknown")
        audit.auth_failure(reason=reason, ip_address=client_ip)
        pulse_auth_failures_total.labels(reason=reason).inc()
    raise
```

Note: Move the `pulse_auth_failures_total.labels(reason=reason).inc()` line outside the `if audit:` block so it always increments even if the audit logger is not initialized:

```python
except HTTPException as exc:
    reason_map = {
        "Token expired": "expired",
        "Invalid token claims": "invalid_claims",
        "Invalid token": "invalid_token",
        "Unknown signing key": "unknown_key",
        "Auth service unavailable": "auth_unavailable",
    }
    reason = reason_map.get(exc.detail, "unknown")
    pulse_auth_failures_total.labels(reason=reason).inc()
    audit = get_audit_logger()
    if audit:
        audit.auth_failure(reason=reason, ip_address=client_ip)
    raise
```

---

## Verification

1. Start the stack and make a few requests:
   ```bash
   curl http://localhost:8081/healthz
   curl http://localhost:8081/customer/devices  # will 401
   curl -H "Authorization: Bearer bad" http://localhost:8081/customer/devices  # will 401
   ```

2. Check metrics:
   ```bash
   curl -s http://localhost:8081/metrics | grep pulse_http_request_duration_seconds
   ```
   Expected output: histogram buckets with `le="0.005"`, `le="0.01"`, etc., and `_count` / `_sum` lines.

3. Check auth failure counter:
   ```bash
   curl -s http://localhost:8081/metrics | grep pulse_auth_failures_total
   ```
   Expected: `pulse_auth_failures_total{reason="invalid_token"} 1.0` (or similar).

4. Check that `/healthz` and `/metrics` paths appear normalized (no UUIDs):
   ```bash
   curl -s http://localhost:8081/metrics | grep path_template
   ```
   Should see paths like `/healthz`, `/customer/devices`, not paths with embedded UUIDs.

## Tests

Existing tests should pass. The new metrics are global singletons and are safe to import in test environments. No mocking is needed -- Prometheus counters/histograms simply accumulate.
