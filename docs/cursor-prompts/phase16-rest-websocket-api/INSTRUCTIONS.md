# Phase 16: REST + WebSocket API Layer

## Goal

Add a clean JSON REST API under `/api/v2/` and a WebSocket endpoint for live telemetry and alert streaming. Enables external dashboards, mobile apps, and third-party integrations to consume device data programmatically.

## Execution Order

Tasks MUST be executed in order. Each task depends on previous tasks.

| # | File | Description | Dependencies |
|---|------|-------------|--------------|
| 1 | `001-cors-api-router.md` | CORS middleware, API v2 router foundation, rate limiting | None |
| 2 | `002-rest-devices-alerts.md` | REST endpoints for devices, alerts, alert rules | #1 |
| 3 | `003-dynamic-telemetry-api.md` | Dynamic InfluxDB telemetry queries + REST endpoints | #1 |
| 4 | `004-websocket-live-data.md` | WebSocket for live telemetry + alert streaming | #1, #3 |
| 5 | `005-tests-and-documentation.md` | Unit tests and README update | #1-#4 |

## Architecture Decisions

1. **Extend existing service**: API added to `ui_iot` FastAPI app (no new service)
2. **Prefix**: All REST endpoints under `/api/v2/`, WebSocket at `/api/v2/ws`
3. **Auth**: Same Keycloak JWT (Bearer header), tenant isolation via RLS
4. **WebSocket auth**: Token as query parameter (`?token=...`) since browsers can't set custom headers on WebSocket connections
5. **WebSocket pattern**: Polling-bridge — server polls InfluxDB/PostgreSQL, pushes to subscribed clients
6. **Dynamic metrics**: `SELECT *` from InfluxDB, filter out metadata columns (same pattern as evaluator)
7. **Rate limiting**: In-memory per-tenant (no extra DB dependency for API rate limits)

## Verification

After each task:
```bash
cd /home/opsconductor/simcloud && python3 -m pytest tests/unit/ -v -x
```
