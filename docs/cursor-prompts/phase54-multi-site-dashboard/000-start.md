# Phase 54: Multi-Site Dashboard

## What Exists

- `sites` table: site_id, tenant_id, name, location, latitude, longitude, created_at
- `device` table: device_id, tenant_id, site_id, status (ONLINE/STALE/OFFLINE)
- `fleet_alert` table: tenant_id, site_id, status (OPEN/ACKNOWLEDGED/CLOSED)
- GET /customer/devices already supports `site_id` filter
- FleetSummaryWidget exists showing tenant-wide ONLINE/STALE/OFFLINE counts

## What This Phase Adds

1. **Backend: GET /customer/sites** — list sites with rollup counts (device count, open alert count, device status breakdown)
2. **Backend: GET /customer/sites/{site_id}/summary** — per-site detail (devices, alerts, last telemetry)
3. **Frontend: SitesPage** — list of sites as cards with status indicators
4. **Frontend: Site detail view** — clicking a site shows its devices and open alerts filtered to that site
5. **Frontend: Navigation** — add Sites to the nav menu

## Execution Order

| Prompt | Description |
|--------|-------------|
| 001 | Backend: GET /customer/sites with rollup |
| 002 | Backend: GET /customer/sites/{site_id}/summary |
| 003 | Frontend: SitesPage (list + cards) |
| 004 | Frontend: Site detail + nav wiring |
| 005 | Unit tests |
| 006 | Verify |

## Key Files

- `services/ui_iot/routes/customer.py` — prompts 001, 002
- `frontend/src/features/sites/` — new directory for prompts 003, 004
- `frontend/src/App.tsx` or router file — navigation (prompt 004)
