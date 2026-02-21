# Phase 127 -- Fleet Map & Telemetry Analytics

## Overview

Two major features for fleet visibility and data exploration:

1. **Fleet Map View** (`/map`) -- Full-page Leaflet map showing all devices with location data, colored by status, with marker clustering and popup detail cards.
2. **Ad-Hoc Telemetry Analytics** (`/analytics`) -- Query builder + time-series chart for exploring telemetry across devices/sites with aggregation, grouping, and CSV export.

**Depends on**: Phase 126 (Customizable Dashboards).

## Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React 19 + TypeScript + Tailwind CSS 4 + Shadcn UI |
| Maps | Leaflet 1.9.4 + react-leaflet 5.0.0 (already installed) |
| Charts | ECharts (via `EChartWrapper`) |
| API | FastAPI + asyncpg |
| Database | PostgreSQL + TimescaleDB (time_bucket) |

## Execution Order

| Step | File | Commit message |
|------|------|---------------|
| 1 | `001-fleet-map-view.md` | `feat: add fleet map page with device markers, clustering, and status colors` |
| 2 | `002-ad-hoc-telemetry-analytics.md` | `feat: add analytics page with query builder, time-series chart, and CSV export` |

## Key Existing Files

| File | Role |
|------|------|
| `frontend/src/app/router.tsx` | React Router config -- add new routes here |
| `frontend/src/components/layout/AppSidebar.tsx` | Sidebar nav -- add Map and Analytics links |
| `frontend/src/features/devices/DeviceMapCard.tsx` | Existing Leaflet usage pattern (imports, tile layer, marker) |
| `frontend/src/services/api/client.ts` | API client (apiGet, apiPost) |
| `frontend/src/services/api/devices.ts` | Device API functions (fetchDevices) |
| `frontend/src/services/api/types.ts` | TypeScript types for Device, etc. |
| `frontend/src/lib/charts/EChartWrapper.tsx` | ECharts wrapper component |
| `frontend/package.json` | leaflet 1.9.4, react-leaflet 5.0.0, @types/leaflet already present |
| `services/ui_iot/routes/devices.py` | Device routes with telemetry history + time_bucket |
| `services/ui_iot/routes/customer.py` | Base customer router with imports (tenant_connection, etc.) |
| `services/ui_iot/app.py` | FastAPI app -- register new routers here |

## Verification After All Steps

1. **Fleet Map** -- Navigate to `/map`. Devices with lat/lng appear as colored circle markers. Click one to see popup with name, status, last seen, and "View Details" link. Zoom out to see clustering. Map auto-refreshes every 60s.
2. **Analytics** -- Navigate to `/analytics`. Select a metric, aggregation, and time range. Click "Run Query". Chart renders with time series lines. Summary stats (min/max/avg) show below query builder. Export to CSV works. Group by device produces multiple series.
3. **Sidebar** -- Both links appear: "Fleet Map" under Fleet group, "Analytics" under Data & Integrations group.
4. **Build** -- `cd frontend && npx tsc --noEmit` passes with no errors.

## Start Now

Read and execute `001-fleet-map-view.md`.
