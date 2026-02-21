# Prompt 003 — Dispatcher: Replace Poll Loop with LISTEN + Fallback Poll

## Context

The dispatcher polls `fleet_alert` every 5 seconds looking for OPEN alerts that need delivery jobs created. After this prompt it wakes immediately when a new `fleet_alert` row is inserted.

## Your Task

**Read `services/dispatcher/dispatcher.py` fully** before making changes.

Apply the same LISTEN pattern as prompt 002 (evaluator), adapted for the dispatcher:

### Channel: `new_fleet_alert`

```python
_notify_event = asyncio.Event()

def on_fleet_alert_notify(conn, pid, channel, payload):
    _notify_event.set()
```

### Replace the poll loop

Same structure as evaluator prompt 002:

```python
FALLBACK_POLL_SECONDS = int(os.getenv("FALLBACK_POLL_SECONDS", "30"))
DEBOUNCE_SECONDS = float(os.getenv("DEBOUNCE_SECONDS", "0.5"))

listener_conn = await create_listener_conn(...)  # same helper pattern as evaluator
await listener_conn.add_listener("new_fleet_alert", on_fleet_alert_notify)

while True:
    try:
        try:
            await asyncio.wait_for(_notify_event.wait(), timeout=FALLBACK_POLL_SECONDS)
        except asyncio.TimeoutError:
            pass  # fallback poll

        _notify_event.clear()
        await asyncio.sleep(DEBOUNCE_SECONDS)
        _notify_event.clear()

        # Run dispatch pass — same logic as before
        async with pool.acquire() as conn:
            # existing dispatch logic here

    except Exception as exc:
        print(f"[dispatcher] error: {exc}")
        await asyncio.sleep(1)
```

If the dispatcher's main loop already has a different structure (e.g., a `run_once()` function called from a loop), adapt accordingly — do NOT redesign the dispatch logic, only change what controls WHEN the loop runs.

Graceful degradation: if LISTEN setup fails, fall back to poll-only with `FALLBACK_POLL_SECONDS` interval.

## Acceptance Criteria

- [ ] Dispatcher listens on `new_fleet_alert` channel
- [ ] Dispatch runs immediately when notification arrives
- [ ] Fallback poll every 30s if no notifications
- [ ] Graceful degradation if LISTEN fails
- [ ] `pytest -m unit -v` passes
