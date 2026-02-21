# Task 004 -- Per-Service Health Metrics

## Commit Message

```
feat(metrics): add queue depth, processing duration, and pool gauges per service
```

## Objective

Add Prometheus gauges and histograms for per-service operational health: queue depths, processing durations, and database connection pool statistics. Instrument each worker's main loop to emit these metrics.

## Files to Modify

1. `services/shared/metrics.py`
2. `services/evaluator_iot/evaluator.py`
3. `services/dispatcher/dispatcher.py`
4. `services/delivery_worker/worker.py`
5. `services/ops_worker/main.py`

---

## Step 1: Add new metrics to shared/metrics.py

**File**: `services/shared/metrics.py`

Add these new metric definitions at the bottom of the file (after the metrics added in task 002):

```python
# Per-service operational metrics
pulse_queue_depth = Gauge(
    "pulse_queue_depth",
    "Current queue depth for a service processing queue",
    ["service", "queue_name"],
)

pulse_processing_duration_seconds = Histogram(
    "pulse_processing_duration_seconds",
    "Duration of a processing cycle in seconds",
    ["service", "operation"],
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0],
)

pulse_db_pool_size = Gauge(
    "pulse_db_pool_size",
    "Current total size of the database connection pool",
    ["service"],
)

pulse_db_pool_free = Gauge(
    "pulse_db_pool_free",
    "Current number of free (idle) connections in the pool",
    ["service"],
)
```

---

## Step 2: Instrument evaluator_iot/evaluator.py

**File**: `services/evaluator_iot/evaluator.py`

### 2a: Import new metrics

Add to the existing imports from `shared.metrics` (around line 15):

```python
from shared.metrics import (
    evaluator_rules_evaluated_total,
    evaluator_alerts_created_total,
    evaluator_evaluation_errors_total,
    pulse_queue_depth,
    pulse_processing_duration_seconds,
    pulse_db_pool_size,
    pulse_db_pool_free,
)
```

### 2b: Track evaluation batch duration

In the main loop (starting at line 1017: `while True:`), wrap the evaluation cycle with timing:

Find the section that starts with:
```python
log_event(logger, "tick_start", tick="evaluator")
```

And ends with:
```python
log_event(logger, "tick_done", tick="evaluator")
```

Add timing around the evaluation work. After `tick_start` and before the actual work begins, record the start time:

```python
eval_start = time.monotonic()
```

After the evaluation cycle completes (just before `log_event(logger, "tick_done", ...)`), observe the duration:

```python
eval_duration = time.monotonic() - eval_start
pulse_processing_duration_seconds.labels(
    service="evaluator",
    operation="evaluation_cycle",
).observe(eval_duration)
```

### 2c: Track device count as queue depth

After `rows = await fetch_rollup_timescaledb(conn)` (line 1038), set the queue depth gauge:

```python
pulse_queue_depth.labels(
    service="evaluator",
    queue_name="devices_to_evaluate",
).set(len(rows))
```

### 2d: Report pool stats

After each evaluation cycle (near `tick_done`), add pool stats reporting:

```python
pulse_db_pool_size.labels(service="evaluator").set(pool.get_size())
pulse_db_pool_free.labels(service="evaluator").set(pool.get_idle_size())
```

Note: `asyncpg.Pool` provides `get_size()` (total connections) and `get_idle_size()` (idle/free connections). These are the correct method names.

### 2e: Also expose metrics via the health server

The evaluator already has a `/metrics` endpoint via the `metrics_handler` at line 86-87 that calls `generate_latest()`. This will automatically include the new metrics because they are global Prometheus registry objects. No changes needed here.

---

## Step 3: Instrument dispatcher/dispatcher.py

**File**: `services/dispatcher/dispatcher.py`

### 3a: Import new metrics

Add imports:

```python
import time
from shared.metrics import (
    pulse_queue_depth,
    pulse_processing_duration_seconds,
    pulse_db_pool_size,
    pulse_db_pool_free,
)
```

Also add the Prometheus endpoint to the health server. The dispatcher currently only has a `/health` endpoint. Add a `/metrics` endpoint.

### 3b: Add /metrics endpoint

In the `start_health_server` function (the second definition, around line 91), add:

```python
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST

async def metrics_handler(request):
    return web.Response(body=generate_latest(), content_type=CONTENT_TYPE_LATEST.split(";")[0])
```

And in the `start_health_server` function, add the route:

```python
app.router.add_get("/metrics", metrics_handler)
```

### 3c: Track dispatch cycle duration

In the main loop (line 410: `while True:`), wrap the dispatch work with timing:

```python
# After the debounce sleep, before acquiring connection:
dispatch_start = time.monotonic()

# ... existing dispatch_once() call ...

# After dispatch_once completes:
dispatch_duration = time.monotonic() - dispatch_start
pulse_processing_duration_seconds.labels(
    service="dispatcher",
    operation="dispatch_cycle",
).observe(dispatch_duration)
```

### 3d: Track pending alerts as queue depth

After `alerts = await fetch_open_alerts(conn)` inside `dispatch_once()` (line 214), add:

```python
pulse_queue_depth.labels(
    service="dispatcher",
    queue_name="pending_alerts",
).set(len(alerts))
```

### 3e: Report pool stats

In the main loop, after each dispatch cycle:

```python
pulse_db_pool_size.labels(service="dispatcher").set(pool.get_size())
pulse_db_pool_free.labels(service="dispatcher").set(pool.get_idle_size())
```

---

## Step 4: Instrument delivery_worker/worker.py

**File**: `services/delivery_worker/worker.py`

### 4a: Import new metrics

Add imports:

```python
from shared.metrics import (
    pulse_queue_depth,
    pulse_processing_duration_seconds,
    pulse_db_pool_size,
    pulse_db_pool_free,
)
```

Also add a Prometheus `/metrics` endpoint. The delivery worker currently only has `/health`.

### 4b: Add /metrics endpoint

In the `start_health_server` function (line 84), add:

```python
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST

async def metrics_handler(request):
    return web.Response(body=generate_latest(), content_type=CONTENT_TYPE_LATEST.split(";")[0])
```

Add the route in `start_health_server`:

```python
app.router.add_get("/metrics", metrics_handler)
```

### 4c: Track delivery attempt duration

In `process_job()` (line 575), the function already tracks `started_at` and `finished_at`. After computing `latency_ms` (line 618), observe the duration:

```python
pulse_processing_duration_seconds.labels(
    service="delivery_worker",
    operation="delivery_attempt",
).observe(latency_ms / 1000.0)
```

### 4d: Track pending jobs as queue depth

In the main loop `run_worker()` (line 887), after `jobs = await fetch_jobs(conn)` (line 948):

```python
pulse_queue_depth.labels(
    service="delivery_worker",
    queue_name="pending_jobs",
).set(len(jobs))
```

Also track notification jobs after `notification_jobs = await fetch_notification_jobs(conn, ...)` (line 952):

```python
pulse_queue_depth.labels(
    service="delivery_worker",
    queue_name="pending_notification_jobs",
).set(len(notification_jobs))
```

### 4e: Report pool stats

In the main loop, after each tick:

```python
pulse_db_pool_size.labels(service="delivery_worker").set(pool.get_size())
pulse_db_pool_free.labels(service="delivery_worker").set(pool.get_idle_size())
```

---

## Step 5: Instrument ops_worker/main.py

**File**: `services/ops_worker/main.py`

### 5a: Import new metrics

Add imports:

```python
import time
from shared.metrics import (
    pulse_processing_duration_seconds,
    pulse_db_pool_size,
    pulse_db_pool_free,
)
```

### 5b: Track worker_loop cycle duration

The `worker_loop` function (line 48) runs each sub-worker on a schedule. Instrument it to track the processing duration of each tick:

```python
async def worker_loop(fn, pool_obj, interval: int) -> None:
    while True:
        trace_token = trace_id_var.set(str(uuid.uuid4()))
        try:
            worker_name = getattr(fn, "__name__", "unknown")
            logger.info("tick_start", extra={"tick": worker_name})
            tick_start = time.monotonic()

            await fn(pool_obj)

            tick_duration = time.monotonic() - tick_start
            pulse_processing_duration_seconds.labels(
                service="ops_worker",
                operation=worker_name,
            ).observe(tick_duration)

            logger.info("tick_done", extra={"tick": worker_name})
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Worker loop failed", extra={"worker": getattr(fn, "__name__", "unknown")})
        finally:
            trace_id_var.reset(trace_token)

        # Report pool stats after each tick
        pulse_db_pool_size.labels(service="ops_worker").set(pool_obj.get_size())
        pulse_db_pool_free.labels(service="ops_worker").set(pool_obj.get_idle_size())

        await asyncio.sleep(interval)
```

### 5c: Ensure ops_worker exposes /metrics

Check if `health_monitor.py` or any other module in ops_worker starts an HTTP server with a `/metrics` endpoint. If not, add one.

Look at `services/ops_worker/health_monitor.py` -- it likely starts an aiohttp server. If it has a `/health` endpoint, add `/metrics` alongside it:

```python
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST

async def metrics_handler(request):
    return web.Response(body=generate_latest(), content_type=CONTENT_TYPE_LATEST.split(";")[0])
```

Add the route in the health server setup.

---

## Step 6: Add pool stats to ui_iot

**File**: `services/ui_iot/app.py`

### 6a: Import new pool metrics

```python
from shared.metrics import pulse_db_pool_size, pulse_db_pool_free
```

### 6b: Report pool stats in /metrics endpoint

In the `/metrics` endpoint (line 423), before `return Response(generate_latest(), ...)`, add:

```python
# Report pool stats
try:
    p = await get_pool()
    pulse_db_pool_size.labels(service="ui_api").set(p.get_size())
    pulse_db_pool_free.labels(service="ui_api").set(p.get_idle_size())
except Exception:
    pass
```

Note: The pool is already acquired earlier in the same function (`p = await get_pool()`), so you can reuse that reference. Place this after the device_rows loop and before the `return` statement.

---

## Verification

1. Start the full stack:
   ```bash
   docker compose up -d
   ```

2. Check ui_iot metrics:
   ```bash
   curl -s http://localhost:8081/metrics | grep pulse_db_pool
   ```
   Expected:
   ```
   pulse_db_pool_size{service="ui_api"} 10.0
   pulse_db_pool_free{service="ui_api"} 8.0
   ```

3. Check evaluator metrics (port 8080 inside container, map accordingly):
   ```bash
   curl -s http://localhost:<evaluator-port>/metrics | grep pulse_processing_duration_seconds
   ```
   Expected: histogram buckets for `operation="evaluation_cycle"`.

4. Check delivery_worker metrics:
   ```bash
   curl -s http://localhost:<delivery-port>/metrics | grep pulse_queue_depth
   ```
   Expected:
   ```
   pulse_queue_depth{service="delivery_worker",queue_name="pending_jobs"} 0.0
   ```

5. Check dispatcher metrics:
   ```bash
   curl -s http://localhost:<dispatcher-port>/metrics | grep pulse_processing_duration_seconds
   ```
   Expected: histogram buckets for `operation="dispatch_cycle"`.

6. Verify all metrics appear in Prometheus (if Prometheus is configured):
   - Navigate to Prometheus UI
   - Query: `pulse_processing_duration_seconds_count`
   - Should see entries for all services

## Tests

Existing tests should pass. The new metrics are global Prometheus registry objects. In test environments, they will simply accumulate values. No mocking needed.

If any tests create `asyncpg.Pool` mocks, ensure those mocks have `get_size()` and `get_idle_size()` methods returning integers. Add these to existing pool mocks:

```python
mock_pool.get_size.return_value = 10
mock_pool.get_idle_size.return_value = 8
```
