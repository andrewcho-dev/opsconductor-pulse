# Phase 57: Telemetry History Charts (Time-Bucketed Aggregates)

## What Exists

- `telemetry` table: TimescaleDB hypertable, columns: `time TIMESTAMPTZ`, `tenant_id TEXT`, `device_id TEXT`, `metrics JSONB`
- `DeviceDetailPage.tsx` exists with `TelemetryChartsSection.tsx` that already shows telemetry charts
- `useDeviceTelemetry()` hook exists for live telemetry
- Evaluator uses raw `now() - interval` queries, not time_bucket

## What This Phase Adds

1. **Backend: GET /customer/devices/{device_id}/telemetry/history** — returns time-bucketed aggregates (avg, min, max per bucket) for a named metric over a time range. Uses TimescaleDB `time_bucket()`.
2. **Frontend: Enhanced TelemetryChartsSection** — connects the existing chart UI to the new history endpoint with a time range selector (1h / 6h / 24h / 7d / 30d). Shows avg line with min/max shaded area.

## What NOT to Change

- Live telemetry WebSocket or `useDeviceTelemetry` hook — leave as-is
- `DeviceDetailPage.tsx` structure — only update `TelemetryChartsSection`

## Execution Order

| Prompt | Description |
|--------|-------------|
| 001 | Backend: GET /customer/devices/{id}/telemetry/history |
| 002 | Frontend: time range selector + history chart wiring |
| 003 | Unit tests |
| 004 | Verify |

## Key Files

- `services/ui_iot/routes/customer.py` — prompt 001
- `frontend/src/features/devices/TelemetryChartsSection.tsx` — prompt 002
- `frontend/src/hooks/use-device-telemetry.ts` (or similar) — prompt 002
- `frontend/src/services/api/devices.ts` — prompt 002
