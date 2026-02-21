# Prompt 002 — Route Services Through PgBouncer

Read `services/shared/db.py` or wherever `create_pool()` / asyncpg pool initialization happens.
Read each service's `.env.example` file.

## Pool Configuration

In each service that creates an asyncpg pool, update the pool sizing:

```python
pool = await asyncpg.create_pool(
    dsn=os.environ["DATABASE_URL"],  # points to PgBouncer
    min_size=2,   # reduced from whatever it was
    max_size=10,  # reduced — PgBouncer multiplexes
    command_timeout=30,
)
```

## Environment Variables

In each service `.env.example`, add a comment:
```
# Use PgBouncer for regular queries (transaction mode)
DATABASE_URL=postgresql://pulse_app:password@pgbouncer:6432/pulse
# Direct DB connection for LISTEN/NOTIFY (see NOTIFY_DATABASE_URL)
NOTIFY_DATABASE_URL=postgresql://pulse_app:password@db:5432/pulse
```

Services that need direct connection (evaluator_iot, dispatcher, delivery_worker):
- Add `NOTIFY_DATABASE_URL` pointing to `db:5432` (not pgbouncer)

Services that do NOT use LISTEN (ingest_iot, provision_api, ops_worker, ui_iot regular queries):
- Only need `DATABASE_URL` → pgbouncer

## Important: SET LOCAL ROLE

PgBouncer transaction mode means `SET LOCAL ROLE` (used in ingest_iot for RLS) works correctly — it's scoped to the transaction. Confirm no service uses `SET ROLE` (session-level) which would persist across connections.

Scan `services/ingest_iot/ingest.py` — if it uses `SET LOCAL ROLE pulse_app`, that is correct for transaction mode.

## Acceptance Criteria

- [ ] Pool min_size/max_size reduced in all services
- [ ] `DATABASE_URL` updated in docker-compose to use pgbouncer host
- [ ] `NOTIFY_DATABASE_URL` env var documented in evaluator/dispatcher/delivery_worker .env.example
- [ ] `SET LOCAL ROLE` confirmed correct (not `SET ROLE`)
