# Task 002 — Carrier Permissions + Plan Feature Gate

## Files

1. Create `db/migrations/107_carrier_permissions.sql`
2. Modify `services/ui_iot/middleware/entitlements.py`
3. Modify `services/ui_iot/routes/carrier.py`
4. Modify `frontend/src/features/settings/CarrierIntegrationsPage.tsx`
5. Modify `frontend/src/services/api/billing.ts` (if needed for type updates)

## Problem

Two issues with carrier integration access:

1. **Missing permissions:** The `carrier.integrations.write`, `carrier.actions.execute`, and `carrier.links.write` permission actions were never seeded into the `permissions` table. All non-operator users get 403.

2. **Missing plan-level feature gate:** Carrier integration CRUD should only be available to tenants on self-service plans. Full-service tenants (where the operator manages carrier on their behalf) should see carrier status in read-only mode but not be able to add/edit/delete integrations.

## Part 1: Migration 107

```sql
-- Migration 107: Carrier permissions + plan feature gate
-- Date: 2026-02-18

-- 1. Insert carrier permission actions (idempotent)
INSERT INTO permissions (action, category, description) VALUES
    ('carrier.integrations.read',   'carrier', 'View carrier integrations'),
    ('carrier.integrations.write',  'carrier', 'Create/update/delete carrier integrations'),
    ('carrier.actions.execute',     'carrier', 'Execute remote carrier actions (activate, suspend, reboot)'),
    ('carrier.links.write',         'carrier', 'Link/unlink devices to carrier integrations')
ON CONFLICT (action) DO NOTHING;

-- 2. Grant ALL carrier permissions to "Full Admin" system role
DO $$
DECLARE
    v_role_id UUID;
BEGIN
    SELECT id INTO v_role_id FROM roles WHERE tenant_id IS NULL AND name = 'Full Admin' AND is_system = true;
    IF v_role_id IS NOT NULL THEN
        INSERT INTO role_permissions (role_id, permission_id)
        SELECT v_role_id, p.id FROM permissions p
        WHERE p.category = 'carrier'
          AND p.id NOT IN (SELECT permission_id FROM role_permissions WHERE role_id = v_role_id)
        ON CONFLICT DO NOTHING;
    END IF;

    -- Device Manager: gets all carrier permissions (they manage devices + connections)
    SELECT id INTO v_role_id FROM roles WHERE tenant_id IS NULL AND name = 'Device Manager' AND is_system = true;
    IF v_role_id IS NOT NULL THEN
        INSERT INTO role_permissions (role_id, permission_id)
        SELECT v_role_id, p.id FROM permissions p
        WHERE p.category = 'carrier'
          AND p.id NOT IN (SELECT permission_id FROM role_permissions WHERE role_id = v_role_id)
        ON CONFLICT DO NOTHING;
    END IF;

    -- Integration Manager: gets integration read/write but not device actions
    SELECT id INTO v_role_id FROM roles WHERE tenant_id IS NULL AND name = 'Integration Manager' AND is_system = true;
    IF v_role_id IS NOT NULL THEN
        INSERT INTO role_permissions (role_id, permission_id)
        SELECT v_role_id, p.id FROM permissions p
        WHERE p.action IN ('carrier.integrations.read', 'carrier.integrations.write')
          AND p.id NOT IN (SELECT permission_id FROM role_permissions WHERE role_id = v_role_id)
        ON CONFLICT DO NOTHING;
    END IF;
END $$;

-- 3. Add carrier_self_service feature flag to plan limits
-- Self-service plans: customers manage their own carrier integrations
-- Managed plans: operator manages carrier on behalf of the customer
UPDATE subscription_plans
SET limits = limits || '{"carrier_self_service": false}'::jsonb
WHERE plan_id = 'starter';

UPDATE subscription_plans
SET limits = limits || '{"carrier_self_service": true}'::jsonb
WHERE plan_id = 'pro';

UPDATE subscription_plans
SET limits = limits || '{"carrier_self_service": true}'::jsonb
WHERE plan_id = 'enterprise';
```

## Part 2: Backend Entitlement Check

In `services/ui_iot/middleware/entitlements.py`, add a new helper function:

```python
async def check_carrier_self_service(conn, tenant_id: str) -> dict:
    """Check if tenant's plan allows self-service carrier management."""
    row = await conn.fetchrow(
        """
        SELECT sp.limits
        FROM subscriptions s
        JOIN subscription_plans sp ON sp.plan_id = s.plan_id
        WHERE s.tenant_id = $1
          AND s.subscription_type = 'MAIN'
          AND s.status IN ('ACTIVE', 'TRIAL')
        ORDER BY s.term_start DESC
        LIMIT 1
        """,
        tenant_id,
    )
    if not row or not row["limits"]:
        return {"allowed": False, "message": "No active subscription"}

    limits = row["limits"] if isinstance(row["limits"], dict) else {}
    allowed = limits.get("carrier_self_service", False)
    return {
        "allowed": allowed,
        "message": "" if allowed else "Carrier integrations are managed by your service provider",
    }
```

## Part 3: Route-Level Gate

In `services/ui_iot/routes/carrier.py`, add the entitlement check to the three write endpoints (create, update, delete integration). The check goes AFTER the permission check but BEFORE the DB write:

```python
from middleware.entitlements import check_carrier_self_service
from middleware.tenant import is_operator

# Inside create_carrier_integration, update_carrier_integration, delete_carrier_integration:
# After permission check passes, before DB write:
if not is_operator():
    async with tenant_connection(pool, tenant_id) as conn:
        gate = await check_carrier_self_service(conn, tenant_id)
        if not gate["allowed"]:
            raise HTTPException(status_code=403, detail=gate["message"])
```

Do NOT gate:
- `GET /carrier/integrations` (read — all customers can see what's configured)
- `GET /devices/{id}/carrier/status` (read)
- `GET /devices/{id}/carrier/usage` (read)
- `GET /devices/{id}/carrier/diagnostics` (read)
- `POST /devices/{id}/carrier/actions/{action}` (actions — all customers can reboot/manage their devices)
- `POST /devices/{id}/carrier/link` (linking — keep gated by permission only, not plan)

Only gate the three integration CRUD write endpoints (create, update, delete).

## Part 4: Frontend — Entitlements-Aware Settings Page

In `CarrierIntegrationsPage.tsx`:

1. Fetch entitlements to check `carrier_self_service`:

```tsx
import { getEntitlements } from "@/services/api/billing";

const entitlementsQuery = useQuery({
  queryKey: ["entitlements"],
  queryFn: getEntitlements,
});

const isSelfService = entitlementsQuery.data?.usage?.carrier_self_service ?? false;
```

Note: The `getEntitlements` endpoint needs to include `carrier_self_service` in its response. Either:
- (a) Add it to the existing `get_plan_usage` function in entitlements.py so it's returned alongside other usage data, OR
- (b) Read it from the plan limits directly in the frontend by calling billing status

Option (a) is cleaner. In `get_plan_usage()`, add `carrier_self_service` to the returned dict:
```python
plan_limits = row["limits"] if row else {}
# ... existing usage aggregation ...
return {
    "plan_id": plan_id,
    "usage": { ... existing ... },
    "features": {
        "carrier_self_service": plan_limits.get("carrier_self_service", False),
    },
}
```

2. Conditionally render UI:

If `isSelfService` is false:
- Hide the "Add Carrier" button
- Hide Edit/Delete buttons on each integration card
- Show an info banner: "Carrier integrations are managed by your service provider. Contact support to make changes."

If `isSelfService` is true:
- Show full CRUD UI (current behavior)

3. Update the TypeScript type for `PlanUsage` in `billing.ts`:

```typescript
export interface PlanUsage {
  plan_id: string | null;
  usage: { ... };
  features?: {
    carrier_self_service?: boolean;
  };
}
```

## Part 5: Apply Migration

After creating the migration file:

```bash
DATABASE_URL="postgresql://iot_user:iot_dev@localhost:5432/iot_db" python3 db/migrate.py
```

Then rebuild/restart the `ui` container.

## Verification

```bash
# Check permissions exist
psql "$DATABASE_URL" -c "SELECT action FROM permissions WHERE category = 'carrier' ORDER BY action;"
# → 4 rows

# Check plan feature flags
psql "$DATABASE_URL" -c "SELECT plan_id, limits->>'carrier_self_service' AS self_service FROM subscription_plans;"
# → starter: false, pro: true, enterprise: true

# Check Full Admin has carrier permissions
psql "$DATABASE_URL" -c "
  SELECT p.action FROM role_permissions rp
  JOIN permissions p ON p.id = rp.permission_id
  JOIN roles r ON r.id = rp.role_id
  WHERE r.name = 'Full Admin' AND p.category = 'carrier'
  ORDER BY p.action;
"
# → 4 rows

# API test (as tenant on 'pro' plan): POST /api/v1/customer/carrier/integrations → 201
# API test (as tenant on 'starter' plan): POST /api/v1/customer/carrier/integrations → 403 "managed by your service provider"
```

```bash
cd frontend && npx tsc --noEmit && npm run build
```
