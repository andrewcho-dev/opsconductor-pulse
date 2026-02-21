# Phase 71: Alert Suppression — Maintenance Windows

## What Exists

- `fleet_alert.silenced_until TIMESTAMPTZ` — per-alert one-time silence (Phase 49)
- `is_silenced(conn, tenant_id, fingerprint)` — evaluator helper that checks `silenced_until > now()`
- No maintenance window table exists
- No recurring/scheduled suppression logic

## What This Phase Adds

**Tenant-scoped maintenance windows** — time periods during which ALL alerts for a tenant (or specific sites/device_types) are suppressed by the evaluator.

1. **Migration**: `alert_maintenance_windows` table
2. **Backend CRUD**: GET/POST/PATCH/DELETE `/customer/maintenance-windows`
3. **Evaluator**: `is_in_maintenance(conn, tenant_id, site_id, device_type)` — checked before `open_or_update_alert()`
4. **Frontend**: Maintenance Windows page

## Maintenance Window Schema

```
tenant_id       TEXT
window_id       TEXT (UUID)
name            TEXT
starts_at       TIMESTAMPTZ       — absolute start
ends_at         TIMESTAMPTZ       — absolute end (NULL = indefinite)
recurring       JSONB NULL        — optional: {dow: [0-6], start_hour: 2, end_hour: 4} for weekly windows
site_ids        TEXT[] NULL       — NULL = all sites
device_types    TEXT[] NULL       — NULL = all device types
enabled         BOOLEAN DEFAULT true
created_at      TIMESTAMPTZ
```

## Execution Order

| Prompt | Description |
|--------|-------------|
| 001 | Migration: alert_maintenance_windows |
| 002 | Backend: maintenance window CRUD |
| 003 | Evaluator: is_in_maintenance() check |
| 004 | Frontend: Maintenance Windows page |
| 005 | Unit tests |
| 006 | Verify |

## Key Files

- `db/migrations/` — prompt 001
- `services/ui_iot/routes/customer.py` — prompt 002
- `services/evaluator_iot/evaluator.py` — prompt 003
- `frontend/src/features/alerts/` — prompt 004
