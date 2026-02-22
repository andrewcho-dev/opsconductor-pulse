# Task 6: Timer-Based Evaluation Loop

## Problem

The main loop currently uses PostgreSQL LISTEN/NOTIFY as its primary trigger:

```python
await asyncio.wait_for(_notify_event.wait(), timeout=fallback_poll_seconds)
```

At 1,000 tenants × 2,000 sensors × 60s intervals the ingest worker fires
`pg_notify('telemetry_inserted', ...)` on every flush (every 500ms). That is
~120 NOTIFY events per minute. The evaluator wakes up 120 times/minute even
though a 60s evaluation interval is all that's needed for window rules.

## Target Behaviour

- The evaluation loop fires on a **60-second clock** regardless of NOTIFY events.
- NOTIFY events are still received and tracked (they identify *which* tenants
  have new data) but do **not** trigger an immediate evaluation cycle on their own.
- A minimum interval guard (`MIN_EVAL_INTERVAL_SECONDS`) prevents evaluation
  from running more frequently than once every N seconds even if explicitly
  requested.
- NOTIFY events continue to be useful: future optimisation (Phase 218) can use
  the `_pending_tenants` set to prioritise which tenants are evaluated first
  within a cycle.

## File — services/evaluator_iot/evaluator.py

### Change 1 — Add constants (already added to compose in Task 1, add to code)

After the existing `POLL_SECONDS` constant (line ~55):

```python
EVALUATION_INTERVAL_SECONDS = int(optional_env("EVALUATION_INTERVAL_SECONDS", "60"))
MIN_EVAL_INTERVAL_SECONDS = int(optional_env("MIN_EVAL_INTERVAL_SECONDS", "10"))
```

### Change 2 — Replace the trigger logic in main()

Locate the current trigger block in `main()` (around lines 1228–1241):

```python
# CURRENT (NOTIFY-primary):
try:
    await asyncio.wait_for(_notify_event.wait(), timeout=fallback_poll_seconds)
except asyncio.TimeoutError:
    log_event(logger, "fallback poll triggered", ...)

_notify_event.clear()
await asyncio.sleep(debounce_seconds)
_notify_event.clear()
_pending_tenants.clear()
```

Replace this block with a timer-primary trigger:

```python
# NEW (timer-primary with minimum interval guard):
_notify_event.clear()

# Sleep until the next scheduled evaluation tick
await asyncio.sleep(EVALUATION_INTERVAL_SECONDS)

# Enforce minimum interval since the last evaluation
since_last = time.monotonic() - _last_eval_monotonic
if since_last < MIN_EVAL_INTERVAL_SECONDS:
    await asyncio.sleep(MIN_EVAL_INTERVAL_SECONDS - since_last)

_notify_event.clear()
_pending_tenants.clear()
```

### Change 3 — Add _last_eval_monotonic tracking

Add a module-level global near the other globals (around line 62):

```python
_last_eval_monotonic: float = 0.0
```

At the END of each successful evaluation cycle (just before `log_event(...,
"tick_done", ...)`) update it:

```python
_last_eval_monotonic = time.monotonic()
```

### Change 4 — Keep the NOTIFY listener running (no changes needed)

The `maintain_notify_listener` task and `on_telemetry_notify` callback are
**unchanged**. NOTIFY events still populate `_pending_tenants` which can be
used for future per-tenant prioritisation. The listener task runs in the
background as before.

Remove the `fallback_poll_seconds` and `debounce_seconds` variables from
`main()` since they are no longer used in the trigger block. (If they are
referenced elsewhere in the function, leave them.)

### Change 5 — Update startup log

After the `shard_config` log added in Task 4, add:

```python
    log_event(
        logger,
        "evaluation_schedule",
        interval_seconds=EVALUATION_INTERVAL_SECONDS,
        min_interval_seconds=MIN_EVAL_INTERVAL_SECONDS,
    )
```

## Result

- Evaluator ticks every 60 seconds
- NOTIFY events are collected but do not trigger extra cycles
- `tick_start` / `tick_done` log lines appear ~once per minute not 120×/min
- POLL_SECONDS env var is no longer the primary driver (can be kept for
  backward compatibility or removed; leave it defined but unused)

## Verification

```bash
docker compose -f compose/docker-compose.yml build evaluator
docker compose -f compose/docker-compose.yml up -d evaluator
docker compose -f compose/docker-compose.yml logs -f evaluator | grep -E "tick_start|tick_done|evaluation_schedule"
```

Confirm:
1. `evaluation_schedule interval_seconds=60` appears at startup
2. `tick_start` and `tick_done` appear approximately every 60 seconds
3. No rapid-fire `tick_start` entries despite ingest NOTIFY events
