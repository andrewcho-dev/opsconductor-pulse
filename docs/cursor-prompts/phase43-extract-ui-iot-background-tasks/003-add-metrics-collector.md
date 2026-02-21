# Prompt 003 — Add Metrics Collector to `ops_worker`

## Context

`ops_worker` now has the health monitor (prompt 002). This prompt adds the metrics collector loop — the second background task being extracted from `ui_iot/app.py`.

## Your Task

### Step 1: Create `services/ops_worker/metrics_collector.py`

Copy the metrics collector logic from `services/ui_iot/app.py` exactly. Same rules as prompt 002:
- Same interval as the original (from audit prompt 001)
- Same tables written to (from audit prompt 001)
- Same DB queries
- No redesign — mechanical extraction only
- No imports from `services/ui_iot/`

### Step 2: Update `services/ops_worker/main.py`

Add the metrics collector to the `asyncio.gather()` call:

```python
async def main():
    await asyncio.gather(
        run_health_monitor(),
        run_metrics_collector(),
    )
```

### Step 3: Verify both loops run independently

The health monitor and metrics collector must run as independent coroutines. A crash in one must NOT kill the other. Wrap each coroutine in a try/except loop:

```python
async def run_health_monitor():
    while True:
        try:
            await _do_health_check()
        except Exception as e:
            logging.error(f"health_monitor error: {e}")
        await asyncio.sleep(HEALTH_MONITOR_INTERVAL)
```

Apply the same pattern to the metrics collector. This is the key resilience improvement over the original — in ui_iot, an unhandled exception in a background task would silently kill that task without restarting.

### Step 4: Environment variables

Both loops likely need:
- `DATABASE_URL` — DB connection string
- Service endpoint URLs for health checking (e.g., `EVALUATOR_URL`, `DISPATCHER_URL`, etc.)

Add a `.env.example` file in `services/ops_worker/` listing all required env vars with placeholder values. Copy the patterns from other services.

## Acceptance Criteria

- [ ] `services/ops_worker/metrics_collector.py` exists with extracted logic
- [ ] `main.py` runs both health monitor and metrics collector concurrently
- [ ] Both loops have try/except crash isolation — a crash in one does NOT crash the other
- [ ] `.env.example` lists all required environment variables
- [ ] `pytest -m unit -v` still passes (ui_iot not changed yet)
