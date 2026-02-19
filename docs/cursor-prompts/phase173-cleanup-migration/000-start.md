# Phase 173 — Cleanup & Data Migration

## Goal

Finalize the transition to the template model: migrate existing device data to new tables, deprecate legacy tables, clean up deprecated frontend components, and update all documentation.

## Prerequisites

- Phases 166-172 all complete
- All new tables and endpoints functional
- Legacy tables (`sensors`, `device_connections`, `normalized_metrics`, `metric_mappings`) still exist with data
- Legacy frontend components still present (MetricsPage, SensorListPage)

## Important Safety Notes

- This phase renames legacy tables with `_deprecated_` prefix rather than dropping them
- Keep `metric_catalog`, `sensors`, and `device_connections` tables temporarily (renamed with `_deprecated_` prefix)
- Data migration is idempotent (uses `ON CONFLICT DO NOTHING`)
- Frontend changes only remove routes/imports — keep deprecated component files for one more phase as rollback safety

## Execution Order

| Step | File | Description |
|------|------|-------------|
| 1 | `001-data-migration.md` | Migration 114: map existing devices to templates |
| 2 | `002-deprecate-tables.md` | Migration 115: rename deprecated tables |
| 3 | `003-frontend-cleanup.md` | Remove deprecated routes and sidebar links |
| 4 | `004-final-docs.md` | Comprehensive doc update across all affected files |

## Verification

```bash
# Migrations apply cleanly
python db/migrate.py

# New tables are populated
psql -c "SELECT count(*) FROM device_sensors;"
psql -c "SELECT count(*) FROM device_transports;"

# Legacy tables are renamed
psql -c "\dt _deprecated_*"

# Frontend builds
cd frontend && npx tsc --noEmit && npm run build

# Full flow test
# Create template → create device → assign module → send telemetry → view in UI
```
