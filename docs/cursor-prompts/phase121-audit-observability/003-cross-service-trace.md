# Task 003 -- Cross-Service Trace ID Propagation

## Commit Message

```
feat(trace): propagate X-Trace-ID across service boundaries
```

## Objective

Ensure trace IDs flow end-to-end across all services. When `ui_iot` makes outbound HTTP calls, it should include the current `trace_id_var` as an `X-Trace-ID` header. Downstream services already read this header (e.g., `TraceMiddleware` at `services/ui_iot/middleware/trace.py` line 20), but outbound calls do not propagate it. Create a shared traced HTTP client helper and retrofit all outbound `httpx.AsyncClient` usage in services.

## Files to Create

1. `services/shared/http_client.py` (new file)

## Files to Modify

1. `services/ui_iot/app.py`
2. `services/ops_worker/health_monitor.py`
3. `services/ops_worker/metrics_collector.py`
4. `services/ops_worker/workers/escalation_worker.py`
5. `services/delivery_worker/worker.py`

---

## Step 1: Create shared/http_client.py

**File**: `services/shared/http_client.py` (NEW)

This module provides a traced HTTP client that automatically injects `X-Trace-ID` from the current ContextVar into all outbound requests.

```python
"""
Traced HTTP client for cross-service trace propagation.

Usage:
    from shared.http_client import traced_client

    async with traced_client(timeout=10.0) as client:
        resp = await client.get("http://other-service/api/data")
        # X-Trace-ID header is automatically injected
"""

import httpx
from contextlib import asynccontextmanager
from typing import AsyncIterator

from shared.logging import trace_id_var


class TraceTransport(httpx.AsyncHTTPTransport):
    """
    httpx transport wrapper that injects X-Trace-ID header
    into every outbound request from the current ContextVar.
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        trace_id = trace_id_var.get("")
        if trace_id:
            request.headers["X-Trace-ID"] = trace_id
        return await super().handle_async_request(request)


@asynccontextmanager
async def traced_client(
    timeout: float = 10.0,
    **kwargs,
) -> AsyncIterator[httpx.AsyncClient]:
    """
    Create an httpx.AsyncClient that auto-injects X-Trace-ID.

    Args:
        timeout: Request timeout in seconds. Default 10.0.
        **kwargs: Additional kwargs passed to httpx.AsyncClient.

    Usage:
        async with traced_client(timeout=5.0) as client:
            resp = await client.get(url)
    """
    transport = TraceTransport()
    async with httpx.AsyncClient(
        transport=transport,
        timeout=timeout,
        **kwargs,
    ) as client:
        yield client
```

### Design notes

- Uses `httpx.AsyncHTTPTransport` subclass to intercept at the transport level. This means the header is injected for every request automatically, including redirects.
- The `trace_id_var.get("")` call returns empty string if no trace ID is set (e.g., in background tasks before the var is set). An empty string means the header is not injected (`if trace_id:` guards this).
- This does NOT use `httpx.EventHook` because event hooks cannot modify request headers in httpx. Transport-level interception is the correct approach.

### Alternative simpler approach

If the `TraceTransport` approach causes issues with httpx version compatibility, use a simpler factory that just sets default headers:

```python
@asynccontextmanager
async def traced_client(
    timeout: float = 10.0,
    **kwargs,
) -> AsyncIterator[httpx.AsyncClient]:
    trace_id = trace_id_var.get("")
    headers = kwargs.pop("headers", {})
    if trace_id:
        headers["X-Trace-ID"] = trace_id
    async with httpx.AsyncClient(
        timeout=timeout,
        headers=headers,
        **kwargs,
    ) as client:
        yield client
```

This simpler version captures the trace ID at client creation time rather than per-request. This is acceptable because in practice the trace ID does not change during a single `async with` block. Use this simpler version if the transport approach encounters any issues.

---

## Step 2: Retrofit ui_iot/app.py outbound calls

**File**: `services/ui_iot/app.py`

### 2a: Add import

```python
from shared.http_client import traced_client
```

### 2b: Replace httpx.AsyncClient usage

There are several places in `app.py` that use `httpx.AsyncClient`:

**OAuth callback** (line 547):
```python
# Before:
async with httpx.AsyncClient(timeout=10.0) as client:
    response = await client.post(token_url, ...)

# After:
async with traced_client(timeout=10.0) as client:
    response = await client.post(token_url, ...)
```

**Token refresh** (line 673):
```python
# Before:
async with httpx.AsyncClient(timeout=10.0) as client:
    response = await client.post(token_url, ...)

# After:
async with traced_client(timeout=10.0) as client:
    response = await client.post(token_url, ...)
```

**Healthz Keycloak check** (line 411):
```python
# Before:
async with httpx.AsyncClient(timeout=2.0) as client:
    r = await client.get(jwks_uri)

# After:
async with traced_client(timeout=2.0) as client:
    r = await client.get(jwks_uri)
```

**Debug auth endpoint** (line 745):
```python
# Before:
async with httpx.AsyncClient(timeout=5.0) as client:
    r = await client.get(...)

# After:
async with traced_client(timeout=5.0) as client:
    r = await client.get(...)
```

### 2c: Keep httpx import

Do NOT remove the `import httpx` line -- it may still be used by other code or as a fallback. However, if after all replacements `httpx` is no longer directly used, the import can be removed.

---

## Step 3: Retrofit ops_worker/health_monitor.py

**File**: `services/ops_worker/health_monitor.py`

### 3a: Add import

```python
from shared.http_client import traced_client
```

### 3b: Replace httpx.AsyncClient

Find the `httpx.AsyncClient` usage (around line 129):

```python
# Before:
async with httpx.AsyncClient(timeout=5.0) as client:
    resp = await client.get(f"{url}/health")

# After:
async with traced_client(timeout=5.0) as client:
    resp = await client.get(f"{url}/health")
```

---

## Step 4: Retrofit ops_worker/metrics_collector.py

**File**: `services/ops_worker/metrics_collector.py`

### 4a: Add import

```python
from shared.http_client import traced_client
```

### 4b: Replace httpx.AsyncClient

Find the `httpx.AsyncClient` usage (around line 79):

```python
# Before:
async with httpx.AsyncClient(timeout=5.0) as client:
    ingest_data = await self._fetch_service_health(client, "ingest", INGEST_URL)

# After:
async with traced_client(timeout=5.0) as client:
    ingest_data = await self._fetch_service_health(client, "ingest", INGEST_URL)
```

---

## Step 5: Retrofit ops_worker/workers/escalation_worker.py

**File**: `services/ops_worker/workers/escalation_worker.py`

### 5a: Add import

```python
from shared.http_client import traced_client
```

### 5b: Replace httpx.AsyncClient

Find the `httpx.AsyncClient` usage (around line 72):

```python
# Before:
async with httpx.AsyncClient(timeout=5.0) as client:
    await client.post(webhook, json=payload)

# After:
async with traced_client(timeout=5.0) as client:
    await client.post(webhook, json=payload)
```

---

## Step 6: Retrofit delivery_worker/worker.py

**File**: `services/delivery_worker/worker.py`

### 6a: Add import

```python
from shared.http_client import traced_client
```

### 6b: Replace httpx.AsyncClient in deliver_webhook

Find the `deliver_webhook` function (line 683). The `httpx.AsyncClient` usage is around line 723:

```python
# Before:
timeout = httpx.Timeout(WORKER_TIMEOUT_SECONDS)
async with httpx.AsyncClient(timeout=timeout) as client:
    resp = await client.post(url, json=request_body, headers=headers)

# After:
async with traced_client(timeout=float(WORKER_TIMEOUT_SECONDS)) as client:
    resp = await client.post(url, json=request_body, headers=headers)
```

### 6c: Replace httpx.AsyncClient in process_notification_job

The `process_notification_job` function has multiple `httpx.AsyncClient` usages for Slack (line 401), Teams (line 417), and PagerDuty (line 435):

For each one:
```python
# Before:
async with httpx.AsyncClient(timeout=WORKER_TIMEOUT_SECONDS) as client:
    resp = await client.post(...)

# After:
async with traced_client(timeout=float(WORKER_TIMEOUT_SECONDS)) as client:
    resp = await client.post(...)
```

### 6d: Keep httpx import

Keep `import httpx` because it is still used for `httpx.Timeout`, `httpx.RequestError`, and potentially other references.

---

## Step 7: Ensure downstream services read X-Trace-ID

The `TraceMiddleware` in `services/ui_iot/middleware/trace.py` already reads the `X-Trace-ID` header (line 20):

```python
trace_id = request.headers.get("X-Trace-ID") or str(uuid.uuid4())
```

Verify that each downstream service that has its own HTTP server (evaluator, dispatcher, delivery_worker use `aiohttp`, not FastAPI) also reads `X-Trace-ID`. Check:

- **evaluator**: Does NOT have an HTTP middleware that reads `X-Trace-ID`. However, it does not receive inbound HTTP requests from ui_iot (it reads from DB). No change needed.
- **dispatcher**: Same as evaluator -- no inbound HTTP from ui_iot. No change needed.
- **delivery_worker**: Same. No change needed.
- **ops_worker**: The `health_monitor` and `metrics_collector` make outbound calls TO other services. They receive no inbound calls from ui_iot. Their `aiohttp` server only handles `/health`. No change needed.

The trace propagation path is:
1. Browser -> ui_iot (TraceMiddleware sets trace_id_var)
2. ui_iot -> Keycloak (X-Trace-ID header via traced_client, informational only)
3. ui_iot -> nothing else (evaluator/dispatcher/delivery are DB-driven, not HTTP-called by ui_iot)

For ops_worker -> other services health checks, the trace_id is set in `worker_loop` (ops_worker/main.py line 50) via `trace_id_var.set(str(uuid.uuid4()))`, so the traced_client will pick it up.

---

## Step 8: Add trace_id to MQTT publish messages (where feasible)

**File**: `services/delivery_worker/worker.py`

In the `deliver_mqtt` function (line 844), when building the MQTT payload, add the current trace_id:

```python
# After building the payload dict (around line 860):
payload = job["payload_json"]
if isinstance(payload, str):
    payload = json.loads(payload)

# Add trace_id to MQTT payload
trace_id = trace_id_var.get("")
if trace_id:
    payload["trace_id"] = trace_id
```

This ensures the trace_id flows through MQTT messages for downstream consumers that may want to correlate.

---

## Verification

1. Make a request to ui_iot:
   ```bash
   curl -v http://localhost:8081/healthz 2>&1 | grep X-Trace-ID
   ```
   Note the returned `X-Trace-ID` value (e.g., `abc123-...`).

2. Check ops_worker logs for the same trace_id:
   ```bash
   docker logs ops_worker 2>&1 | grep "abc123"
   ```
   If ops_worker called ui_iot's health endpoint with traced_client, its logs should show the trace_id.

3. Verify the traced_client works by checking that outbound calls from ui_iot include the header:
   ```bash
   # In dev, you can temporarily add logging to the oauth callback to verify
   # Or check Keycloak access logs for the X-Trace-ID header
   ```

## Tests

Existing tests should pass. The `traced_client` function is a drop-in replacement for `httpx.AsyncClient`. If tests mock `httpx.AsyncClient`, they may need to be updated to mock `shared.http_client.traced_client` instead. Check for mocks in:
- `tests/integration/test_delivery_pipeline.py` (lines 107, 285, 336) -- these mock `services.delivery_worker.worker.httpx.AsyncClient`. After this change, the deliver_webhook function uses `traced_client`, so mocks need updating. Either:
  - Mock `services.delivery_worker.worker.traced_client` instead, OR
  - Keep a local alias in worker.py: `from shared.http_client import traced_client` and mock that path.
