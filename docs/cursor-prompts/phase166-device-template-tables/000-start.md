# Phase 166 — Device Template Tables

## Goal

Create the foundational database schema for the unified device template model. This introduces `device_templates`, `template_metrics`, `template_commands`, and `template_slots` tables, plus seed data for known Lifeline hardware.

## Prerequisites

- All migrations through 108 applied
- PostgreSQL with TimescaleDB extension
- Existing `tenants` table and RLS infrastructure (`pulse_app`, `pulse_operator` roles)

## Architecture

```
device_templates (1)
├── template_metrics (N)    — what this device type can measure
├── template_commands (N)   — what commands it accepts
└── template_slots (N)      — expansion ports / bus interfaces
    └── compatible_templates INT[]  — which module templates fit this slot
```

**Key design principle:** Templates define **capability**; instances (Phase 167) define **reality**.

- `tenant_id IS NULL` → system template, visible to all tenants
- `tenant_id = X` → tenant-owned template, private
- `is_locked = true` → system templates cannot be edited by tenants

## Execution Order

| Step | File | Description |
|------|------|-------------|
| 1 | `001-template-schema.md` | Migration 109: 4 tables + RLS + indexes |
| 2 | `002-seed-templates.md` | Migration 110: seed Lifeline system templates |
| 3 | `003-update-docs.md` | Update database and architecture docs |

## Verification

```bash
# After running migrations:
python db/migrate.py

# Verify tables exist
psql -c "\dt" | grep -E "device_templates|template_metrics|template_commands|template_slots"

# Verify seed data
psql -c "SELECT id, name, category, source FROM device_templates WHERE tenant_id IS NULL;"

# Verify RLS policies
psql -c "SELECT tablename, policyname FROM pg_policies WHERE tablename LIKE 'device_template%' OR tablename LIKE 'template_%';"
```
