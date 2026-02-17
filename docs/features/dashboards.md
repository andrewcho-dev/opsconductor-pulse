---
last-verified: 2026-02-17
sources:
  - services/ui_iot/routes/dashboards.py
  - frontend/src/features/dashboard/
  - frontend/src/features/operator/
phases: [17, 66, 81, 82, 83, 84, 85, 86, 87, 126, 142]
---

# Dashboards

> Customer dashboards and operator NOC command center views.

## Overview

Dashboards provide live operational visibility:

- Customer dashboards summarize fleet status and alert activity.
- Operator dashboards provide cross-tenant NOC/command-center views.

## How It Works

- Dashboards are stored server-side and rendered client-side.
- Widgets include fleet status, device counts, KPI tiles, alert feeds, and charts.
- Live updates are driven by WebSocket/SSE streams and periodic refresh.

## Database Schema

Key tables (high-level):

- Dashboard definitions (dashboards + widgets + layout structures)
- Supporting time-series: `telemetry`, `system_metrics`

## API Endpoints

See: [Customer Endpoints](../api/customer-endpoints.md).

Dashboard CRUD:

- `/api/v1/customer/dashboards*`

Streaming:

- WebSocket/SSE described in [WebSocket Protocol](../api/websocket-protocol.md)

## Frontend

Primary modules:

- `frontend/src/features/dashboard/` — customer dashboards
- `frontend/src/features/operator/` — operator dashboards (NOC, tenant matrix, etc.)

## Configuration

- Refresh cadence and polling intervals are controlled by UI defaults and backend tuning.
- Monitoring stack provides additional ops dashboards via Grafana (separate from app dashboards).

## See Also

- [Monitoring](../operations/monitoring.md)
- [WebSocket Protocol](../api/websocket-protocol.md)
- [Service: ui-iot](../services/ui-iot.md)

