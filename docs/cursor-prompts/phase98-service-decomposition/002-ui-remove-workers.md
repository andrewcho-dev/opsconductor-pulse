# Phase 98 — Remove Workers from ui_iot app.py

## Only do this AFTER step 001 is verified working in ops_worker.

## File to modify
`services/ui_iot/app.py`

## Step 1: Remove the worker imports

Find and delete these import lines at the top of app.py:
```python
from workers.escalation_worker import run_escalation_tick
from workers.report_worker import run_report_tick
```

## Step 2: Remove the background task registrations

Find the startup event handler (likely `@app.on_event("startup")` or `@app.lifespan`).
Delete these two lines:
```python
background_tasks.append(asyncio.create_task(worker_loop(run_escalation_tick, pool, interval=60)))
background_tasks.append(asyncio.create_task(worker_loop(run_report_tick, pool, interval=86400)))
```

Do NOT remove any other background task registrations (batch_writer, audit_logger).

## Step 3: Check if worker_loop helper is still needed

After removing the two tasks, check if `worker_loop()` is still used by any remaining
background tasks in app.py. If it is still used, keep it. If nothing else calls it,
delete the `worker_loop()` function definition too.

## Step 4: Check if workers/ package is still needed in ui_iot

After the import removals, check if any other file in `services/ui_iot/` imports from
`workers/`. Search:
```bash
rg "from workers\." services/ui_iot/ --type py
rg "import workers" services/ui_iot/ --type py
```

If nothing else imports from `workers/`, you can leave the `workers/` directory in place
(it doesn't hurt anything) or delete it — Cursor's choice. The Dockerfile COPY statement
for workers can stay either way.

## Step 5: Rebuild ui_iot

```bash
docker compose -f compose/docker-compose.yml build ui
docker compose -f compose/docker-compose.yml up -d ui
docker compose -f compose/docker-compose.yml logs ui --tail=20
```

Expected: clean startup, no references to escalation_worker or report_worker in ui logs.
API endpoints still respond (401 for unauthenticated requests).
