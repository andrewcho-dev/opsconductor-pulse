# Prompt 002 — Evaluator: Replace Poll Loop with LISTEN + Fallback Poll

## Context

`services/evaluator_iot/evaluator.py` currently runs an infinite loop with `await asyncio.sleep(POLL_SECONDS)` (5 seconds). It wakes every 5 seconds, evaluates all devices, and sleeps again.

After this prompt it will:
1. LISTEN on `new_telemetry` channel — wake immediately when telemetry arrives
2. Debounce: collect notifications for 0.5s, then run one evaluation pass for unique tenant_ids received
3. Keep a 30s fallback poll — if no notifications arrive for 30s, run a full evaluation pass anyway (safety net)

## Your Task

**Read `services/evaluator_iot/evaluator.py` fully** before making changes.

### Step 1: Add a LISTEN connection helper

Add this helper to `evaluator.py`:

```python
async def create_listener_conn(host, port, database, user, password):
    """Create a dedicated asyncpg connection for LISTEN (not from pool)."""
    return await asyncpg.connect(
        host=host, port=port, database=database, user=user, password=password
    )
```

### Step 2: Add debounce logic

```python
import collections

# Shared state between listener callback and evaluation loop
_pending_tenants: set[str] = set()
_notify_event = asyncio.Event()

def on_telemetry_notify(conn, pid, channel, payload):
    """Called by asyncpg when a new_telemetry notification arrives."""
    tenant_id = payload.strip()
    if tenant_id:
        _pending_tenants.add(tenant_id)
    _notify_event.set()
```

### Step 3: Replace the main loop in `main()`

The current structure is:
```python
while True:
    try:
        async with pool.acquire() as conn:
            rows = await fetch_rollup_timescaledb(conn)
            # ... evaluate all devices
    except Exception as exc:
        ...
    await asyncio.sleep(POLL_SECONDS)
```

Replace with:

```python
FALLBACK_POLL_SECONDS = int(os.getenv("FALLBACK_POLL_SECONDS", "30"))
DEBOUNCE_SECONDS = float(os.getenv("DEBOUNCE_SECONDS", "0.5"))

# Create dedicated listener connection
listener_conn = await create_listener_conn(PG_HOST, PG_PORT, PG_DB, PG_USER, PG_PASS)
await listener_conn.add_listener("new_telemetry", on_telemetry_notify)
print("[evaluator] LISTEN on new_telemetry channel active")

while True:
    try:
        # Wait for a notification OR fallback poll timeout
        try:
            await asyncio.wait_for(
                _notify_event.wait(),
                timeout=FALLBACK_POLL_SECONDS
            )
        except asyncio.TimeoutError:
            print("[evaluator] fallback poll (no notifications received)")

        # Clear the event and collect pending tenants
        _notify_event.clear()
        await asyncio.sleep(DEBOUNCE_SECONDS)  # debounce window
        _notify_event.clear()

        # Run evaluation pass
        async with pool.acquire() as conn:
            rows = await fetch_rollup_timescaledb(conn)
            # ... same evaluation logic as before ...

    except Exception as exc:
        COUNTERS["evaluation_errors"] += 1
        print(f"[evaluator] error={type(exc).__name__} {exc}")
        await asyncio.sleep(1)  # brief pause on error before retry
```

**Important:** The `_pending_tenants` set is available for future optimization (evaluate only notified tenants). For now, evaluation still runs across all devices — the LISTEN just controls WHEN the loop runs, not what it evaluates. This is the safest minimal change.

### Step 4: Handle listener connection loss

Wrap the listener setup in a try/except. If the listener connection drops, log a warning and fall back to polling until reconnected. Do NOT crash — the fallback poll keeps the system working.

```python
try:
    listener_conn = await create_listener_conn(...)
    await listener_conn.add_listener("new_telemetry", on_telemetry_notify)
except Exception as e:
    print(f"[evaluator] WARNING: LISTEN setup failed, using poll-only mode: {e}")
    listener_conn = None
    # Loop will rely entirely on FALLBACK_POLL_SECONDS timeout
```

## Acceptance Criteria

- [ ] Evaluator listens on `new_telemetry` channel
- [ ] Evaluation runs immediately when notification arrives (not waiting for 5s sleep)
- [ ] Fallback poll still runs every 30s if no notifications
- [ ] Evaluator does NOT crash if LISTEN setup fails — degrades to poll-only
- [ ] `POLL_SECONDS` env var is no longer the primary timing control (kept for backwards compat but unused by default)
- [ ] `pytest -m unit -v` passes — existing evaluator tests must not regress
