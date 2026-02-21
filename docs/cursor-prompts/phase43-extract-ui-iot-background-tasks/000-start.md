# Phase 43: Extract ui_iot Background Tasks → New `ops_worker` Service

## Why This Phase

The architecture audit found that `services/ui_iot/app.py` does too many things simultaneously:
- Serves the REST API and WebSocket endpoints
- Hosts the React SPA (static files)
- Acts as Keycloak admin client
- Runs 4 background tasks inline:
  1. **Health monitor** — polls all services every 60s, writes to `service_health` table
  2. **Metrics collector** — polls DB every 5s, aggregates capacity/usage metrics
  3. **Batch writer** — flushes telemetry batches (shared via `ingest_core.py`)
  4. **Audit logger** — periodic flush of audit events

**The risk:** A bug or crash in any background task kills the entire UI API. The health monitor polling a dead service could block the event loop. The metrics collector hitting a slow DB query delays the REST API.

**The fix:** Extract the **health monitor** and **metrics collector** into a new `ops_worker` service. These are read-heavy, polling tasks that should not share a process with the user-facing API.

The **batch writer** stays in ui_iot (it is tightly coupled to the HTTP ingest path). The **audit logger** stays in ui_iot (it flushes in-memory events from the request context).

## What the New Service Does

New service: `services/ops_worker/`
- Runs the health monitor loop (every 60s)
- Runs the metrics collector loop (every 5s)
- Has no HTTP endpoints (no FastAPI app needed — plain asyncio)
- Writes to the same PostgreSQL DB (uses existing pool pattern)
- Deployed as a new container in `docker-compose.yml`

## What Changes in ui_iot

`services/ui_iot/app.py`:
- Remove the health monitor background task
- Remove the metrics collector background task
- Keep batch writer startup/shutdown
- Keep audit logger startup/shutdown
- The `/operator/system/*` routes still READ from `service_health` and metrics tables — they do not need to collect data themselves

## Execution Order

| Prompt | Description | Priority |
|--------|-------------|----------|
| 001 | Audit `ui_iot/app.py` background tasks — map exact code to extract | CRITICAL |
| 002 | Create `services/ops_worker/` with health monitor loop | HIGH |
| 003 | Add metrics collector loop to `ops_worker` | HIGH |
| 004 | Remove extracted tasks from `ui_iot/app.py` | HIGH |
| 005 | Add `ops_worker` to `docker-compose.yml` | HIGH |
| 006 | Unit tests for `ops_worker` health monitor + metrics collector | HIGH |
| 007 | Verify full suite + integration smoke test | CRITICAL |

## Verification After All Prompts Complete

```bash
# Unit tests
pytest -m unit -v

# Service starts
docker compose up ops_worker --build -d
docker compose logs ops_worker

# ui_iot still serves API
docker compose up ui_iot --build -d
curl http://localhost:8000/health

# Operator system dashboard still works (reads from DB written by ops_worker)
# Manual: login as operator, navigate to System Dashboard, confirm metrics display
```

## Key Files

- `services/ui_iot/app.py` — source of extraction (4 background tasks defined here)
- `services/ui_iot/routes/system.py` — reads `service_health` + metrics tables (must NOT change)
- `services/shared/` — shared DB pool, models, utilities for new service to import
- `docker-compose.yml` — add new service
- `tests/unit/` — add tests for new service
