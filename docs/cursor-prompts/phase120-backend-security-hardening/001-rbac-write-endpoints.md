# 001: RBAC Enforcement on Write Endpoints

## Context

Migration 080 (`db/migrations/080_iam_permissions.sql`) created the permissions table and seeded 28 permissions with 6 system roles. The `require_permission()` dependency in `services/ui_iot/middleware/permissions.py` (line 119-125) is implemented but only applied to alert-rule CRUD endpoints via `require_customer_admin`. Most write endpoints only check `require_customer` (verifies the user has a customer/tenant-admin realm role and belongs to an org) but do NOT enforce granular permissions.

The existing permission actions from migration 080 use a coarse-grained pattern like `devices.write`, `alerts.acknowledge`. This task adds finer-grained actions for specific operations and wires them into every write endpoint.

## Step 1: Create Migration 081

Create file: `db/migrations/081_rbac_write_permissions.sql`

This migration adds new fine-grained permission rows and assigns them to the appropriate system roles. Some of these overlap with existing 080 permissions -- use `ON CONFLICT (action) DO NOTHING` to be idempotent.

```sql
-- Migration 081: Fine-grained write permissions for all mutating endpoints
-- Date: 2026-02-16

-- New permission rows (idempotent)
INSERT INTO permissions (action, category, description) VALUES
    -- Devices (some already exist in 080, those will be skipped)
    ('devices.create',        'devices',      'Create/provision new devices'),
    ('devices.update',        'devices',      'Update device properties'),
    ('devices.delete',        'devices',      'Delete devices'),
    ('devices.decommission',  'devices',      'Decommission devices'),
    ('devices.import',        'devices',      'Bulk import devices via CSV'),
    ('devices.tokens.rotate', 'devices',      'Rotate device API tokens'),
    ('devices.tokens.revoke', 'devices',      'Revoke device API tokens'),
    ('devices.tags.write',    'devices',      'Add/remove/set device tags'),
    ('devices.groups.write',  'devices',      'Manage device groups'),
    ('devices.twin.write',    'devices',      'Update device twin desired state'),
    ('devices.commands.send', 'devices',      'Send commands to devices'),

    -- Alerts
    ('alerts.acknowledge',    'alerts',       'Acknowledge alerts'),
    ('alerts.close',          'alerts',       'Close/resolve alerts'),
    ('alerts.silence',        'alerts',       'Silence alerts'),
    ('alerts.digest.write',   'alerts',       'Manage alert digest settings'),

    -- Alert rules
    ('alert-rules.create',    'alert-rules',  'Create alert rules'),
    ('alert-rules.update',    'alert-rules',  'Update alert rules'),
    ('alert-rules.delete',    'alert-rules',  'Delete alert rules'),
    ('alert-rules.templates', 'alert-rules',  'Apply alert rule templates'),

    -- Notifications
    ('notifications.create',  'notifications','Create notification channels'),
    ('notifications.update',  'notifications','Update notification channels'),
    ('notifications.delete',  'notifications','Delete notification channels'),
    ('notifications.test',    'notifications','Test notification channels'),
    ('notifications.routing.create', 'notifications', 'Create routing rules'),
    ('notifications.routing.update', 'notifications', 'Update routing rules'),
    ('notifications.routing.delete', 'notifications', 'Delete routing rules'),

    -- Escalation
    ('escalation.create',     'escalation',   'Create escalation policies'),
    ('escalation.update',     'escalation',   'Update escalation policies'),
    ('escalation.delete',     'escalation',   'Delete escalation policies'),

    -- On-call
    ('oncall.create',         'oncall',       'Create on-call schedules'),
    ('oncall.update',         'oncall',       'Update on-call schedules'),
    ('oncall.delete',         'oncall',       'Delete on-call schedules'),
    ('oncall.layers.write',   'oncall',       'Manage on-call layers'),
    ('oncall.overrides.write','oncall',       'Manage on-call overrides'),

    -- Maintenance
    ('maintenance.create',    'maintenance',  'Create maintenance windows'),
    ('maintenance.update',    'maintenance',  'Update maintenance windows'),
    ('maintenance.delete',    'maintenance',  'Delete maintenance windows')
ON CONFLICT (action) DO NOTHING;

-- Grant ALL new permissions to "Full Admin" system role.
-- Full Admin already gets all permissions via the blanket INSERT in 080,
-- but if these were added after the role was created, we need to backfill.
DO $$
DECLARE
    v_role_id UUID;
BEGIN
    SELECT id INTO v_role_id FROM roles WHERE tenant_id IS NULL AND name = 'Full Admin' AND is_system = true;
    IF v_role_id IS NOT NULL THEN
        INSERT INTO role_permissions (role_id, permission_id)
        SELECT v_role_id, p.id FROM permissions p
        WHERE p.id NOT IN (SELECT permission_id FROM role_permissions WHERE role_id = v_role_id)
        ON CONFLICT DO NOTHING;
    END IF;

    -- Device Manager: add device-specific write permissions
    SELECT id INTO v_role_id FROM roles WHERE tenant_id IS NULL AND name = 'Device Manager' AND is_system = true;
    IF v_role_id IS NOT NULL THEN
        INSERT INTO role_permissions (role_id, permission_id)
        SELECT v_role_id, p.id FROM permissions p
        WHERE p.action IN (
            'devices.create', 'devices.update', 'devices.delete', 'devices.decommission',
            'devices.import', 'devices.tokens.rotate', 'devices.tokens.revoke',
            'devices.tags.write', 'devices.groups.write', 'devices.twin.write',
            'devices.commands.send',
            'maintenance.create', 'maintenance.update', 'maintenance.delete'
        )
        ON CONFLICT DO NOTHING;
    END IF;

    -- Alert Manager: add alert and alert-rule write permissions
    SELECT id INTO v_role_id FROM roles WHERE tenant_id IS NULL AND name = 'Alert Manager' AND is_system = true;
    IF v_role_id IS NOT NULL THEN
        INSERT INTO role_permissions (role_id, permission_id)
        SELECT v_role_id, p.id FROM permissions p
        WHERE p.action IN (
            'alerts.acknowledge', 'alerts.close', 'alerts.silence', 'alerts.digest.write',
            'alert-rules.create', 'alert-rules.update', 'alert-rules.delete', 'alert-rules.templates',
            'maintenance.create', 'maintenance.update', 'maintenance.delete'
        )
        ON CONFLICT DO NOTHING;
    END IF;

    -- Integration Manager: add notification write permissions
    SELECT id INTO v_role_id FROM roles WHERE tenant_id IS NULL AND name = 'Integration Manager' AND is_system = true;
    IF v_role_id IS NOT NULL THEN
        INSERT INTO role_permissions (role_id, permission_id)
        SELECT v_role_id, p.id FROM permissions p
        WHERE p.action IN (
            'notifications.create', 'notifications.update', 'notifications.delete', 'notifications.test',
            'notifications.routing.create', 'notifications.routing.update', 'notifications.routing.delete',
            'escalation.create', 'escalation.update', 'escalation.delete',
            'oncall.create', 'oncall.update', 'oncall.delete',
            'oncall.layers.write', 'oncall.overrides.write'
        )
        ON CONFLICT DO NOTHING;
    END IF;

    -- Viewer: gets NO write permissions (already correct from 080, but confirm)
    -- No action needed.
END $$;
```

## Step 2: Apply `require_permission()` to Write Endpoints

### Import Pattern

In each route file, add the import at the top:

```python
from middleware.permissions import require_permission
```

**IMPORTANT**: `require_permission()` returns a `Depends()` object. It must be added as an **endpoint-level dependency**, not a router-level dependency. The router already has `Depends(JWTBearer()), Depends(inject_tenant_context), Depends(require_customer)` -- those remain.

The pattern for applying to an endpoint is:

```python
@router.post("/devices", status_code=201, dependencies=[require_permission("devices.create")])
async def create_device(...):
```

### File: `services/ui_iot/routes/devices.py`

The file uses `from routes.customer import *` (line 3) which already imports everything needed. Add the import:

After line 3 (`from routes.customer import *  # noqa: F401,F403`), add:
```python
from middleware.permissions import require_permission
```

Apply to these endpoints:

| Line | Endpoint | Decorator Change | Permission |
|------|----------|-----------------|------------|
| 101 | `@router.post("/devices", status_code=201)` | Add `dependencies=[require_permission("devices.create")]` | `devices.create` |
| 264 | `@router.post("/devices/import")` | Add `dependencies=[require_permission("devices.import")]` | `devices.import` |
| 186 | `@router.delete("/devices/{device_id}/tokens/{token_id}", status_code=204)` | Add `dependencies=[require_permission("devices.tokens.revoke")]` | `devices.tokens.revoke` |
| 213 | `@router.post("/devices/{device_id}/tokens/rotate", status_code=201)` | Add `dependencies=[require_permission("devices.tokens.rotate")]` | `devices.tokens.rotate` |
| 620 | `@router.delete("/devices/{device_id}")` | Add `dependencies=[require_permission("devices.delete")]` | `devices.delete` |
| 822 | `@router.patch("/devices/{device_id}")` | Add `dependencies=[require_permission("devices.update")]` | `devices.update` |
| 924 | `@router.patch("/devices/{device_id}/decommission", ...)` | Replace `dependencies=[Depends(require_customer)]` with `dependencies=[require_permission("devices.decommission")]` | `devices.decommission` |
| 990 | `@router.patch("/devices/{device_id}/twin/desired")` | Add `dependencies=[require_permission("devices.twin.write")]` | `devices.twin.write` |
| 1050 | `@router.post("/devices/{device_id}/commands", status_code=201)` | Add `dependencies=[require_permission("devices.commands.send")]` | `devices.commands.send` |
| 1208 | `@router.put("/devices/{device_id}/tags")` | Add `dependencies=[require_permission("devices.tags.write")]` | `devices.tags.write` |
| 1246 | `@router.post("/devices/{device_id}/tags/{tag}")` | Add `dependencies=[require_permission("devices.tags.write")]` | `devices.tags.write` |
| 1283 | `@router.delete("/devices/{device_id}/tags/{tag}")` | Add `dependencies=[require_permission("devices.tags.write")]` | `devices.tags.write` |
| 1366 | `@router.post("/device-groups", status_code=201)` | Add `dependencies=[require_permission("devices.groups.write")]` | `devices.groups.write` |
| 1395 | `@router.patch("/device-groups/{group_id}")` | Add `dependencies=[require_permission("devices.groups.write")]` | `devices.groups.write` |
| 1429 | `@router.delete("/device-groups/{group_id}")` | Add `dependencies=[require_permission("devices.groups.write")]` | `devices.groups.write` |
| 1483 | `@router.put("/device-groups/{group_id}/devices/{device_id}")` | Add `dependencies=[require_permission("devices.groups.write")]` | `devices.groups.write` |
| 1521 | `@router.delete("/device-groups/{group_id}/devices/{device_id}")` | Add `dependencies=[require_permission("devices.groups.write")]` | `devices.groups.write` |
| 1566 | `@router.post("/maintenance-windows", status_code=201)` | Add `dependencies=[require_permission("maintenance.create")]` | `maintenance.create` |
| 1596 | `@router.patch("/maintenance-windows/{window_id}")` | Add `dependencies=[require_permission("maintenance.update")]` | `maintenance.update` |
| 1644 | `@router.delete("/maintenance-windows/{window_id}")` | Add `dependencies=[require_permission("maintenance.delete")]` | `maintenance.delete` |

### File: `services/ui_iot/routes/alerts.py`

The file uses `from routes.customer import *` (line 3). Add the import:

After line 3, add:
```python
from middleware.permissions import require_permission
```

Apply to these endpoints:

| Line | Endpoint | Change | Permission |
|------|----------|--------|------------|
| 43 | `@router.put("/alert-digest-settings")` | Add `dependencies=[require_permission("alerts.digest.write")]` | `alerts.digest.write` |
| 148 | `@router.patch("/alerts/{alert_id}/acknowledge", dependencies=[Depends(require_customer)])` | Replace `dependencies=[Depends(require_customer)]` with `dependencies=[require_permission("alerts.acknowledge")]` | `alerts.acknowledge` |
| 189 | `@router.patch("/alerts/{alert_id}/close", dependencies=[Depends(require_customer)])` | Replace `dependencies=[Depends(require_customer)]` with `dependencies=[require_permission("alerts.close")]` | `alerts.close` |
| 224 | `@router.patch("/alerts/{alert_id}/silence", dependencies=[Depends(require_customer)])` | Replace `dependencies=[Depends(require_customer)]` with `dependencies=[require_permission("alerts.silence")]` | `alerts.silence` |
| 276 | `@router.post("/alert-rule-templates/apply", dependencies=[Depends(require_customer)])` | Replace `dependencies=[Depends(require_customer)]` with `dependencies=[require_permission("alert-rules.templates")]` | `alert-rules.templates` |
| 363 | `@router.post("/alert-rules", dependencies=[Depends(require_customer_admin)])` | Replace `dependencies=[Depends(require_customer_admin)]` with `dependencies=[require_permission("alert-rules.create")]` | `alert-rules.create` |
| 481 | `@router.patch("/alert-rules/{rule_id}", dependencies=[Depends(require_customer_admin)])` | Replace `dependencies=[Depends(require_customer_admin)]` with `dependencies=[require_permission("alert-rules.update")]` | `alert-rules.update` |
| 600 | `@router.delete("/alert-rules/{rule_id}", dependencies=[Depends(require_customer_admin)])` | Replace `dependencies=[Depends(require_customer_admin)]` with `dependencies=[require_permission("alert-rules.delete")]` | `alert-rules.delete` |

### File: `services/ui_iot/routes/notifications.py`

Add import after line 13 (`from notifications.senders import ...`):
```python
from middleware.permissions import require_permission
```

Apply to these endpoints:

| Line | Endpoint | Change | Permission |
|------|----------|--------|------------|
| 120 | `@router.post("/notification-channels", ...)` | Add `dependencies=[require_permission("notifications.create")]` | `notifications.create` |
| 162 | `@router.put("/notification-channels/{channel_id}", ...)` | Add `dependencies=[require_permission("notifications.update")]` | `notifications.update` |
| 188 | `@router.delete("/notification-channels/{channel_id}", ...)` | Add `dependencies=[require_permission("notifications.delete")]` | `notifications.delete` |
| 202 | `@router.post("/notification-channels/{channel_id}/test")` | Add `dependencies=[require_permission("notifications.test")]` | `notifications.test` |
| 272 | `@router.post("/notification-routing-rules", ...)` | Add `dependencies=[require_permission("notifications.routing.create")]` | `notifications.routing.create` |
| 302 | `@router.put("/notification-routing-rules/{rule_id}", ...)` | Add `dependencies=[require_permission("notifications.routing.update")]` | `notifications.routing.update` |
| 336 | `@router.delete("/notification-routing-rules/{rule_id}", ...)` | Add `dependencies=[require_permission("notifications.routing.delete")]` | `notifications.routing.delete` |

### File: `services/ui_iot/routes/escalation.py`

Add import after line 11 (`from dependencies import get_db_pool`):
```python
from middleware.permissions import require_permission
```

Apply to these endpoints:

| Line | Endpoint | Change | Permission |
|------|----------|--------|------------|
| 104 | `@router.post("/escalation-policies", ...)` | Add `dependencies=[require_permission("escalation.create")]` | `escalation.create` |
| 154 | `@router.put("/escalation-policies/{policy_id}", ...)` | Add `dependencies=[require_permission("escalation.update")]` | `escalation.update` |
| 207 | `@router.delete("/escalation-policies/{policy_id}", ...)` | Add `dependencies=[require_permission("escalation.delete")]` | `escalation.delete` |

### File: `services/ui_iot/routes/oncall.py`

Add import after line 11 (`from oncall.resolver import ...`):
```python
from middleware.permissions import require_permission
```

Apply to these endpoints:

| Line | Endpoint | Change | Permission |
|------|----------|--------|------------|
| 94 | `@router.post("/oncall-schedules", status_code=201)` | Add `dependencies=[require_permission("oncall.create")]` | `oncall.create` |
| 140 | `@router.put("/oncall-schedules/{schedule_id}")` | Add `dependencies=[require_permission("oncall.update")]` | `oncall.update` |
| 184 | `@router.delete("/oncall-schedules/{schedule_id}", status_code=204)` | Add `dependencies=[require_permission("oncall.delete")]` | `oncall.delete` |
| 198 | `@router.post("/oncall-schedules/{schedule_id}/layers", status_code=201)` | Add `dependencies=[require_permission("oncall.layers.write")]` | `oncall.layers.write` |
| 229 | `@router.put("/oncall-schedules/{schedule_id}/layers/{layer_id}")` | Add `dependencies=[require_permission("oncall.layers.write")]` | `oncall.layers.write` |
| 262 | `@router.delete("/oncall-schedules/{schedule_id}/layers/{layer_id}", status_code=204)` | Add `dependencies=[require_permission("oncall.layers.write")]` | `oncall.layers.write` |
| 302 | `@router.post("/oncall-schedules/{schedule_id}/overrides", status_code=201)` | Add `dependencies=[require_permission("oncall.overrides.write")]` | `oncall.overrides.write` |
| 329 | `@router.delete("/oncall-schedules/{schedule_id}/overrides/{override_id}", status_code=204)` | Add `dependencies=[require_permission("oncall.overrides.write")]` | `oncall.overrides.write` |

## Step 3: Update seed_demo_data.py

In `scripts/seed_demo_data.py`, the current seed does not populate permissions or role assignments for demo tenants. Add a function that ensures the demo admin user gets "Full Admin" role assigned for both tenant-a and tenant-b.

Find the section that creates users/tenants and add after it:

```python
async def seed_role_assignments(conn):
    """Assign Full Admin role to demo admin users."""
    full_admin = await conn.fetchrow(
        "SELECT id FROM roles WHERE name = 'Full Admin' AND is_system = true AND tenant_id IS NULL"
    )
    if not full_admin:
        print("  [skip] Full Admin role not found (run migration 080+081 first)")
        return

    role_id = full_admin["id"]
    for tenant_id in TENANTS:
        # Assign to demo admin user (sub = 'demo-admin-{tenant}')
        await conn.execute(
            """
            INSERT INTO user_role_assignments (tenant_id, user_id, role_id, assigned_by)
            VALUES ($1, $2, $3, 'seed-script')
            ON CONFLICT (tenant_id, user_id, role_id) DO NOTHING
            """,
            tenant_id,
            f"demo-admin-{tenant_id}",
            role_id,
        )
    print("  [ok] Role assignments seeded")
```

Call `await seed_role_assignments(conn)` from the main seed function.

## Verification

```bash
# 1. Apply migration
psql "$DATABASE_URL" -f db/migrations/081_rbac_write_permissions.sql

# 2. Verify permissions were inserted
psql "$DATABASE_URL" -c "SELECT COUNT(*) FROM permissions;"
# Should be 28 (from 080) + new ones = ~60+

# 3. Verify Full Admin has all permissions
psql "$DATABASE_URL" -c "
  SELECT COUNT(*) FROM role_permissions rp
  JOIN roles r ON r.id = rp.role_id
  WHERE r.name = 'Full Admin' AND r.is_system = true;
"
# Should match total permission count

# 4. Verify Viewer has NO write permissions
psql "$DATABASE_URL" -c "
  SELECT p.action FROM role_permissions rp
  JOIN roles r ON r.id = rp.role_id
  JOIN permissions p ON p.id = rp.permission_id
  WHERE r.name = 'Viewer' AND r.is_system = true
  ORDER BY p.action;
"
# Should show only *.read and dashboard.read, settings.read, etc.

# 5. Integration test: Viewer role gets 403
# Get token for Viewer-role user, then:
curl -X POST http://localhost:8080/customer/devices \
  -H "Authorization: Bearer $VIEWER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"device_id": "test", "site_id": "test"}' \
  --write-out "\n%{http_code}"
# Expected: 403

# 6. Integration test: Full Admin can create
curl -X POST http://localhost:8080/customer/devices \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"device_id": "test", "site_id": "test"}' \
  --write-out "\n%{http_code}"
# Expected: 201

# 7. Run existing tests to confirm no regressions
cd services/ui_iot && python -m pytest tests/ -x -q
```

## Notes

- `require_permission()` already handles operator bypass (operators get `"*"` in their permission set -- see `permissions.py` line 89-90).
- `require_permission()` internally calls `inject_tenant_context` via its dependency chain, so it is safe to use alongside the router-level `inject_tenant_context`.
- For endpoints that had `dependencies=[Depends(require_customer)]` or `dependencies=[Depends(require_customer_admin)]`, replace the entire dependencies list with `dependencies=[require_permission("...")]` since `require_permission()` already depends on `inject_tenant_context` which triggers the tenant context setup.
- The router-level dependencies (`JWTBearer`, `inject_tenant_context`, `require_customer`) still run first. Adding endpoint-level `require_permission` adds a second, finer-grained check.
