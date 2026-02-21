# Phase 62: Telemetry CSV Export

## What Exists

- `telemetry` table: `time`, `tenant_id`, `device_id`, `site_id`, `msg_type`, `seq`, `metrics` (JSONB)
- `GET /customer/devices/{id}/telemetry/history` — returns JSON bucketed aggregates
- No CSV export endpoint exists

## What This Phase Adds

1. **Backend: GET /customer/devices/{id}/telemetry/export** — raw telemetry rows flattened to CSV. Each metric key in the JSONB becomes a column. Supports same range params (1h/6h/24h/7d/30d) plus a `limit` cap (max 10000 rows).
2. **Frontend: "Download CSV" button** on DeviceDetailPage (in TelemetryChartsSection or nearby) — triggers the export endpoint and downloads the file.

## Execution Order

| Prompt | Description |
|--------|-------------|
| 001 | Backend: GET /customer/devices/{id}/telemetry/export |
| 002 | Frontend: Download CSV button |
| 003 | Unit tests |
| 004 | Verify |

## Key Files

- `services/ui_iot/routes/customer.py` — prompt 001
- `frontend/src/features/devices/TelemetryChartsSection.tsx` — prompt 002
- `frontend/src/services/api/devices.ts` — prompt 002
