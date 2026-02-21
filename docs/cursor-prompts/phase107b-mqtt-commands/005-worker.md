# Phase 107b — Command TTL Expiry Worker (ops_worker)

## Context

The command expiry tick runs in `services/ops_worker` alongside the jobs
expiry tick added in Phase 108. It marks `queued` commands as `missed` or
`expired` after their `expires_at` has passed.

## Distinction: missed vs expired

- `missed` — command was published to MQTT (`published_at IS NOT NULL`) but
  the device never ACKed. The device was likely offline or didn't subscribe.
- `expired` — command was never published (MQTT broker was unavailable at
  creation time). The command never reached the broker.

## File to modify
`services/ops_worker/workers/jobs_worker.py`

Or create `services/ops_worker/workers/commands_worker.py` and import it
in `main.py` — follow the same pattern as `jobs_worker.py`.

## Add the commands expiry tick

```python
from shared.log import get_logger, trace_id_var
import uuid

logger = get_logger("pulse.commands_worker")


async def run_commands_expiry_tick(pool) -> None:
    """
    Mark queued commands as missed or expired after expires_at passes.

    missed  — was published (published_at set) but not ACKed before TTL
    expired — was never published (broker was down at creation time)

    Non-fatal: exceptions are logged and swallowed.
    """
    token = trace_id_var.set(str(uuid.uuid4()))
    try:
        async with pool.acquire() as conn:
            # Missed: published but not ACKed
            missed = await conn.execute(
                """
                UPDATE device_commands
                SET status = 'missed'
                WHERE status      = 'queued'
                  AND expires_at <= NOW()
                  AND published_at IS NOT NULL
                """,
            )

            # Expired: never published
            expired = await conn.execute(
                """
                UPDATE device_commands
                SET status = 'expired'
                WHERE status      = 'queued'
                  AND expires_at <= NOW()
                  AND published_at IS NULL
                """,
            )

            total = int(missed.split()[-1]) + int(expired.split()[-1])
            if total > 0:
                logger.info(
                    "commands_expiry_tick",
                    extra={"missed": missed.split()[-1], "expired": expired.split()[-1]},
                )
    except Exception as exc:
        logger.exception("commands_expiry_tick_error", extra={"error": str(exc)})
    finally:
        trace_id_var.reset(token)
```

## Schedule in main.py

In `services/ops_worker/main.py`, import and schedule alongside the jobs tick:

```python
from workers.commands_worker import run_commands_expiry_tick  # adjust path

# In the main loop:
await run_commands_expiry_tick(pool)
```

Run at the same 60-second cadence — no separate scheduling needed.

## Verify

```bash
docker logs iot-ops-worker --tail=20 | grep command
```

No log output is normal if there are no expired commands yet.
Create a command, backdate its `expires_at` in the DB, wait 60s, then check:

```bash
docker exec iot-postgres psql -U iot iotcloud -c \
  "SELECT command_id, status FROM device_commands ORDER BY created_at DESC LIMIT 5;"
```
