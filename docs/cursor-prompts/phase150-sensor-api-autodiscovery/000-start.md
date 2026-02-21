# Phase 150 — Sensor API & Auto-Discovery

## Overview

Phase 149 created the database tables (`sensors`, `device_connections`, `device_health_telemetry`). This phase builds the backend API layer:

1. **Sensor CRUD endpoints** — List, create, update, delete sensors on a device
2. **Sensor auto-discovery in ingestor** — When telemetry arrives with new metric keys, auto-create sensor records
3. **Device connection endpoints** — CRUD for cellular connection data
4. **Device health telemetry endpoint** — Query platform diagnostics for a device
5. **Updated device detail endpoint** — Include sensors and connection info

## Execution Order

1. `001-sensors-route.md` — New `routes/sensors.py` with full CRUD
2. `002-sensor-autodiscovery.md` — Hook in `ingest.py` to auto-create sensors from metric keys
3. `003-device-connections-route.md` — Endpoints for cellular connection data
4. `004-device-health-endpoint.md` — Endpoint for platform health telemetry
5. `005-device-detail-expansion.md` — Expand GET device detail to include sensors + connection
6. `006-register-routes.md` — Wire new routes into `app.py`

## Key Patterns (match existing codebase)

- Routes use `APIRouter(prefix="/api/v1/customer", dependencies=[JWTBearer, inject_tenant_context, require_customer])`
- DB access via `tenant_connection(pool, tenant_id)` context manager
- Pydantic models for request validation
- `get_tenant_id()` and `get_user()` from middleware
- Error handling: re-raise HTTPException, catch all others → log + 500
- Ingestor uses `self.pool.acquire()` directly (not tenant_connection) with `_set_tenant_write_context()`
