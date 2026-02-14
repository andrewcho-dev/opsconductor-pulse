# Phase 98 — Add Escalation + Report Workers to ops_worker

## Step 1: Find the ops_worker entry point

Read `services/ops_worker/` directory. Find the main file (likely `worker.py` or `main.py`).
Read it to understand how existing ticks are registered (health check, metrics collection).

## Step 2: Copy worker modules into ops_worker

The worker functions live in `services/ui_iot/workers/`:
- `services/ui_iot/workers/escalation_worker.py` — `run_escalation_tick(pool)`
- `services/ui_iot/workers/report_worker.py` — `run_report_tick(pool)`
- `services/ui_iot/oncall/resolver.py` — used by escalation_worker

Copy these into ops_worker:
```
services/ops_worker/workers/escalation_worker.py  ← copy from ui_iot/workers/
services/ops_worker/workers/report_worker.py      ← copy from ui_iot/workers/
services/ops_worker/oncall/resolver.py            ← copy from ui_iot/oncall/
```

Create `services/ops_worker/workers/__init__.py` and `services/ops_worker/oncall/__init__.py`
if they don't exist.

## Step 3: Register the ticks in ops_worker main loop

In the ops_worker main file, add the two new ticks alongside existing ones.
Follow the exact same pattern already used for health/metrics ticks:

```python
from workers.escalation_worker import run_escalation_tick
from workers.report_worker import run_report_tick

# In the main async loop or startup, alongside existing ticks:
asyncio.create_task(worker_loop(run_escalation_tick, pool, interval=60))
asyncio.create_task(worker_loop(run_report_tick, pool, interval=86400))
```

If ops_worker uses a different pattern (e.g., a list of `(fn, interval)` tuples), follow
that pattern instead.

## Step 4: Update ops_worker Dockerfile

Ensure the new directories are copied into the Docker image.
Read `services/ops_worker/Dockerfile` and add COPY statements for any new directories:

```dockerfile
COPY workers /app/workers
COPY oncall /app/oncall
```

Only add lines that are not already there.

## Step 5: Check DB connection in ops_worker

ops_worker already connects to the DB (for health checks and metrics). Confirm it uses the
same pool pattern as ui_iot. The escalation_worker and report_worker expect an asyncpg pool
passed as `pool` — verify the ops_worker pool setup matches.

If ops_worker passes the pool differently (e.g., a connection string), adapt the import
call accordingly.

## Step 6: Rebuild ops_worker

```bash
docker compose -f compose/docker-compose.yml build ops_worker
docker compose -f compose/docker-compose.yml up -d ops_worker
docker compose -f compose/docker-compose.yml logs ops_worker --tail=30
```

Expected: no import errors, both new workers start without error in the logs.
