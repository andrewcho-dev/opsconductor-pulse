# Prompt 004 — Delivery Worker: Replace Poll Loop with LISTEN + Fallback Poll

## Context

The delivery worker polls `delivery_jobs` every 2 seconds looking for PENDING jobs. After this prompt it wakes immediately when a new delivery job is inserted.

## Your Task

**Read `services/delivery_worker/worker.py` fully** before making changes.

Apply the same LISTEN pattern as prompts 002 and 003, adapted for delivery worker:

### Channel: `new_delivery_job`

```python
_notify_event = asyncio.Event()

def on_delivery_job_notify(conn, pid, channel, payload):
    _notify_event.set()
```

### Replace the poll loop

Same structure as previous prompts:

```python
FALLBACK_POLL_SECONDS = int(os.getenv("FALLBACK_POLL_SECONDS", "15"))  # delivery: 15s fallback
DEBOUNCE_SECONDS = float(os.getenv("DEBOUNCE_SECONDS", "0.1"))  # delivery: 100ms debounce (faster)

listener_conn = await create_listener_conn(...)
await listener_conn.add_listener("new_delivery_job", on_delivery_job_notify)

while True:
    try:
        try:
            await asyncio.wait_for(_notify_event.wait(), timeout=FALLBACK_POLL_SECONDS)
        except asyncio.TimeoutError:
            pass

        _notify_event.clear()
        await asyncio.sleep(DEBOUNCE_SECONDS)
        _notify_event.clear()

        # Run delivery pass — same logic as before

    except Exception as exc:
        print(f"[delivery_worker] error: {exc}")
        await asyncio.sleep(1)
```

Note: delivery worker uses a shorter debounce (100ms) and fallback (15s) because delivery latency is more visible to end users (webhook/email/SNMP targets).

Graceful degradation: if LISTEN setup fails, fall back to poll-only.

## Acceptance Criteria

- [ ] Delivery worker listens on `new_delivery_job` channel
- [ ] Delivery runs immediately when notification arrives
- [ ] Fallback poll every 15s if no notifications
- [ ] Graceful degradation if LISTEN fails
- [ ] `pytest -m unit -v` passes
