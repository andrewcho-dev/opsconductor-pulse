# Phase 138 — Deprecation Cleanup & UI Polish

## Goal
Remove dead code (deprecated services), replace `window.confirm()` with AlertDialog, add map marker clustering.

## Current State
- 2 deprecated services still in docker-compose.yml: `dispatcher` (lines 161-198) and `delivery_worker` (lines 200-241)
- 3 `window.confirm()` calls in frontend
- FleetMapPage has a TODO for marker clustering (line 13)
- `tenant_subscription` table was already removed in migration 032

## Execution Order
1. `001-remove-deprecated-services.md` — Remove dispatcher and delivery_worker from compose + source dirs
2. `002-replace-window-confirm.md` — Replace 3 window.confirm() with AlertDialog
3. `003-map-clustering.md` — Add leaflet.markercluster to FleetMapPage

## Verification (after all tasks)
```bash
docker compose config --quiet     # validates compose file
docker compose up -d              # all services start
cd frontend && npm run build      # no errors
```
