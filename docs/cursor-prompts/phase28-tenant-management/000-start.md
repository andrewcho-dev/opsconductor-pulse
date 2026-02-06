# Phase 28: Operator Tenant Management

## Overview

Build a complete tenant management system for operators. Currently tenants only exist as JWT claims — no explicit tenant registry, no provisioning workflow, no status dashboard.

## Current State

| Component | Status |
|-----------|--------|
| Tenant table | ❌ Does not exist |
| Tenant CRUD API | ❌ Does not exist |
| Tenant provisioning | ❌ Manual (Keycloak + InfluxDB separately) |
| Tenant status/stats | ❌ No aggregation |
| Operator tenant UI | ❌ Does not exist |

## What We'll Build

1. **tenants table** — Explicit tenant registry with metadata
2. **Tenant CRUD API** — Operator endpoints for tenant management
3. **Tenant provisioning** — Auto-create InfluxDB database on tenant creation
4. **Tenant stats API** — Aggregate device/alert/integration counts
5. **Operator UI** — Tenant list, detail, and create pages

## Execute Prompts In Order

1. `001-tenants-table.md` — Create tenants table with migration
2. `002-tenant-crud-api.md` — Add operator CRUD endpoints
3. `003-tenant-stats-api.md` — Add tenant stats/status endpoint
4. `004-tenant-provisioning.md` — Auto-provision InfluxDB on create
5. `005-operator-tenant-ui.md` — Build operator tenant pages

## Key Files

| File | Role |
|------|------|
| `db/migrations/018_tenants_table.sql` | NEW — Tenants table |
| `services/ui_iot/routes/operator.py` | Add tenant endpoints |
| `services/ui_iot/db/queries.py` | Add tenant queries |
| `frontend/src/features/operator/` | Tenant UI pages |

## Tenant Lifecycle

```
1. Operator creates tenant via UI/API
   → Insert into tenants table
   → Create InfluxDB database telemetry_{tenant_id}

2. Operator creates user in Keycloak (manual for now)
   → Set tenant_id attribute
   → Set role attribute

3. Customer logs in
   → JWT contains tenant_id claim
   → RLS enforces isolation

4. Operator views tenant status
   → Device count, alert count, last activity
   → Integration/rule counts
```

## Start Now

Read and execute `001-tenants-table.md`.
