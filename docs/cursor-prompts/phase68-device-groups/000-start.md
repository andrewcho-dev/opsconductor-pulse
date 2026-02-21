# Phase 68: Device Group Management

## What Exists

- `device` table with `tenant_id`, `device_id`, `name`, `status`, `site_id`, `device_type`, `tags`
- `device_tags` table: `(tenant_id, device_id, tag)` — used for filtering but no group-level features
- `alert_rules` table: has `site_ids TEXT[]` for scoping rules to sites
- No `device_groups` table exists

## What This Phase Adds

1. **Migration**: `device_groups` table + `device_group_members` junction table
2. **Backend CRUD**: GET/POST/PATCH/DELETE `/customer/device-groups`
3. **Backend membership**: PUT/DELETE `/customer/device-groups/{id}/devices/{device_id}`
4. **Group-scoped alert rules**: Add `group_ids TEXT[]` to `alert_rules` (alongside existing `site_ids`)
5. **Frontend**: Device Groups page — list, create, edit, add/remove members
6. **Frontend**: Group selector in alert rule form

## Execution Order

| Prompt | Description |
|--------|-------------|
| 001 | Migration: device_groups + device_group_members |
| 002 | Backend: device group CRUD |
| 003 | Backend: group membership endpoints |
| 004 | Backend: group_ids on alert_rules |
| 005 | Frontend: Device Groups page |
| 006 | Frontend: group selector in alert rule form |
| 007 | Unit tests |
| 008 | Verify |

## Key Files

- `db/migrations/` — prompt 001
- `services/ui_iot/routes/customer.py` — prompts 002–004
- `frontend/src/features/devices/DeviceGroupsPage.tsx` — new, prompt 005
- `frontend/src/features/alerts/AlertRuleDialog.tsx` — prompt 006
