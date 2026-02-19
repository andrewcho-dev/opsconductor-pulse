# Phase 167 — Device Instance Tables

## Goal

Create the instance-level tables that link real devices to templates: `device_modules` (physical modules in slots), `device_sensors` (restructured sensor model), `device_transports` (replaces `device_connections`), and add `template_id`/`parent_device_id` FKs to `device_registry`.

## Prerequisites

- Phase 166 complete (migrations 109-110 applied)
- Existing `sensors` and `device_connections` tables (migrations 099, 100)
- Existing `device_registry` table with extended identity fields (migration 102)

## Architecture

```
device_registry
├── template_id FK → device_templates        (what type is this device?)
├── parent_device_id FK → device_registry    (gateway hierarchy)
├── device_modules (N)                       (physical modules in slots)
│   └── module_template_id FK → device_templates (category=expansion_module)
├── device_sensors (N)                       (active measurement points)
│   ├── template_metric_id FK → template_metrics (if modeled)
│   └── device_module_id FK → device_modules     (if from a module)
└── device_transports (N)                    (ingestion + connectivity config)
```

## Execution Order

| Step | File | Description |
|------|------|-------------|
| 1 | `001-device-modules.md` | Migration 111: device_modules table |
| 2 | `002-sensors-transports.md` | Migration 112: device_sensors + device_transports + data copy |
| 3 | `003-registry-updates.md` | Migration 113: device_registry FK additions |
| 4 | `004-update-docs.md` | Update database docs |

## Verification

```bash
python db/migrate.py

psql -c "\dt" | grep -E "device_modules|device_sensors|device_transports"
psql -c "\d device_registry" | grep -E "template_id|parent_device_id"

# Verify data migration from sensors → device_sensors
psql -c "SELECT count(*) FROM sensors; SELECT count(*) FROM device_sensors;"
# Counts should match

# Verify data migration from device_connections → device_transports
psql -c "SELECT count(*) FROM device_connections; SELECT count(*) FROM device_transports;"
```
