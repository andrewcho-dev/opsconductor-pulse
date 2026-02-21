# Phase 73: Operator Metrics Dashboard (Prometheus Frontend)

## What Exists

- Phase 58 added Prometheus /metrics endpoints on ui_iot, ingest_iot, evaluator_iot
- `services/shared/metrics.py` — metric objects (counters/gauges)
- Backend operator endpoints ALREADY EXIST:
  - `GET /operator/system/metrics` — current system metrics snapshot
  - `GET /operator/system/metrics/history` — historical metrics
  - `GET /operator/system/metrics/history/batch` — batch historical fetch
  - `GET /operator/system/metrics/latest` — latest snapshot
- ECharts is the PRIMARY charting library in the frontend (`echarts ^6.0.0`)
- `frontend/src/lib/charts/EChartWrapper.tsx` — ECharts wrapper component
- No frontend page currently displays Prometheus metrics

## What This Phase Adds (Frontend Only — No Backend Changes)

1. **`frontend/src/features/operator/SystemMetricsPage.tsx`** — new operator page
2. **Charts**: ECharts time-series showing key metrics:
   - Ingest rate (messages/min) over last hour
   - Active alert count by tenant
   - Delivery job failure rate
   - Device status breakdown (ONLINE/STALE/OFFLINE)
3. **Auto-refresh** every 30 seconds
4. **Navigation**: "System Metrics" link in operator nav

## Execution Order

| Prompt | Description |
|--------|-------------|
| 001 | API client functions for operator metrics |
| 002 | SystemMetricsPage with ECharts |
| 003 | Nav + route wiring |
| 004 | Unit tests |
| 005 | Verify |

## Key Files

- `frontend/src/services/api/operator.ts` — prompt 001
- `frontend/src/features/operator/SystemMetricsPage.tsx` — new, prompt 002
- `frontend/src/lib/charts/EChartWrapper.tsx` — read before writing charts
- `frontend/src/app/router.tsx` — prompt 003
