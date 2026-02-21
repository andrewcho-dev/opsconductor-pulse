# Prompt 003 — LISTEN/NOTIFY Direct-Connect Bypass

Read the LISTEN/NOTIFY usage in:
- `services/evaluator_iot/evaluator.py`
- `services/dispatcher/dispatcher.py`
- `services/delivery_worker/worker.py`

These services call `conn.add_listener()` / `await conn.execute("LISTEN ...")`.
This does NOT work through PgBouncer in transaction mode.

## Change

In each service, maintain TWO connections:
1. **Regular queries** — use the asyncpg pool (via PgBouncer / `DATABASE_URL`)
2. **LISTEN connection** — a single dedicated asyncpg connection direct to PostgreSQL (`NOTIFY_DATABASE_URL`)

Pattern:
```python
import os

# In startup / main():
notify_dsn = os.environ.get("NOTIFY_DATABASE_URL", os.environ["DATABASE_URL"])
notify_conn = await asyncpg.connect(notify_dsn)
await notify_conn.add_listener("new_telemetry", callback)

# Regular queries still use the pool:
async with pool.acquire() as conn:
    rows = await conn.fetch(...)
```

On shutdown, close the notify_conn:
```python
await notify_conn.remove_listener("new_telemetry", callback)
await notify_conn.close()
```

Do NOT change the callback logic or fallback polling — only change the connection used for LISTEN.

## Acceptance Criteria

- [ ] evaluator_iot uses dedicated `notify_conn` for LISTEN, pool for queries
- [ ] dispatcher uses dedicated `notify_conn` for LISTEN
- [ ] delivery_worker uses dedicated `notify_conn` for LISTEN
- [ ] `NOTIFY_DATABASE_URL` read from env (falls back to `DATABASE_URL` if not set)
- [ ] notify_conn closed cleanly on shutdown
- [ ] `pytest -m unit -v` passes
