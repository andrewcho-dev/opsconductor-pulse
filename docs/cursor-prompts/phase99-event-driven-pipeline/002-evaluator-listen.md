# Phase 99 — Update Evaluator to LISTEN/NOTIFY

## File to modify
`services/evaluator/evaluator.py`

## Current behavior

The evaluator loops with `await asyncio.sleep(POLL_SECONDS)` (default 5s) regardless of
whether new telemetry arrived. It re-evaluates all devices on every tick.

## New behavior

The evaluator waits for a `telemetry_inserted` NOTIFY from PostgreSQL (or a 5s timeout
as fallback), then immediately runs the evaluation cycle.

## Pattern to implement

This is the same pattern the dispatcher already uses. Follow it exactly.

Look at `services/dispatcher/dispatcher.py` to find how it implements LISTEN/NOTIFY
with `asyncio.wait_for` and a fallback poll interval. Mirror that structure.

The key pattern:

```python
import asyncio
import asyncpg

# Module-level event that gets set when a NOTIFY arrives
_notify_event = asyncio.Event()

def _handle_notify(connection, pid, channel, payload):
    """Called by asyncpg when a NOTIFY arrives on the subscribed channel."""
    _notify_event.set()

async def run_evaluator(pool):
    # Acquire a dedicated listener connection (separate from the pool)
    listener_conn = await asyncpg.connect(DATABASE_URL)
    await listener_conn.add_listener("telemetry_inserted", _handle_notify)

    try:
        while True:
            # Wait for NOTIFY or fall back to poll after POLL_SECONDS
            try:
                await asyncio.wait_for(
                    _notify_event.wait(),
                    timeout=POLL_SECONDS  # fallback: still evaluate every 5s
                )
            except asyncio.TimeoutError:
                pass  # timeout is normal — just run the evaluation cycle
            finally:
                _notify_event.clear()

            # Run the evaluation cycle
            await evaluate_all_devices(pool)

    finally:
        await listener_conn.remove_listener("telemetry_inserted", _handle_notify)
        await listener_conn.close()
```

## Important implementation notes

1. **Dedicated listener connection** — asyncpg requires a dedicated connection for LISTEN
   (cannot use a pool connection that gets returned between uses). Keep it open for the
   process lifetime.

2. **DATABASE_URL** — use the same env var the evaluator already uses for its pool.

3. **Fallback poll** — `POLL_SECONDS` (default 5) stays as the maximum wait. If NOTIFY is
   missed for any reason, the evaluator still runs within 5 seconds.

4. **Thread safety** — `_handle_notify` is called from asyncpg's async callback. Since
   asyncio.Event is not thread-safe across loops, confirm the evaluator runs in a single
   event loop (it should — it's a simple async process).

5. **Reconnect on listener connection failure** — wrap the listener connection in a
   reconnect loop in case the DB connection drops:

```python
async def maintain_listener(notify_event: asyncio.Event):
    """Keep a LISTEN connection alive, reconnect on drop."""
    while True:
        try:
            conn = await asyncpg.connect(DATABASE_URL)
            await conn.add_listener("telemetry_inserted",
                lambda *_: notify_event.set())
            # Wait until connection closes
            await conn.wait_closed()
        except Exception:
            logger.warning("Listener connection lost, reconnecting in 2s")
            await asyncio.sleep(2)
```

Run this as a separate asyncio task alongside the main evaluation loop.

## Rebuild evaluator

```bash
docker compose -f compose/docker-compose.yml build evaluator
docker compose -f compose/docker-compose.yml up -d evaluator
docker compose -f compose/docker-compose.yml logs evaluator --tail=30
```

Expected: evaluator starts and shows LISTEN established.
