# 004: Deprecation Cleanup - Remove Legacy tenant_subscription

## Task

Remove the deprecated `tenant_subscription` table and all references to it after confirming the new `subscriptions` table is working correctly.

**IMPORTANT:** Only run this AFTER:
1. Phase 32 fully deployed and tested
2. Data migration (031) completed successfully
3. All services using new `subscriptions` table
4. At least 1 week of production operation

## Files to Create/Update

1. `db/migrations/032_remove_tenant_subscription.sql` (NEW)
2. `services/ui_iot/services/subscription.py` (CLEANUP)
3. `services/ui_iot/routes/customer.py` (CLEANUP)
4. `services/ui_iot/routes/operator.py` (CLEANUP)

## 1. Database Migration

**File:** `db/migrations/032_remove_tenant_subscription.sql`

```sql
-- Migration: Remove deprecated tenant_subscription table
-- IMPORTANT: Run only after confirming subscriptions table is working
-- Prerequisites:
--   - All data migrated to subscriptions table
--   - All services updated to use subscriptions table
--   - At least 1 week of stable operation

-- Step 1: Verify no orphaned devices (should return 0)
DO $$
DECLARE
    orphan_count INT;
BEGIN
    SELECT COUNT(*) INTO orphan_count
    FROM device_registry
    WHERE subscription_id IS NULL
      AND status = 'ACTIVE';

    IF orphan_count > 0 THEN
        RAISE EXCEPTION 'Cannot proceed: % active devices without subscription', orphan_count;
    END IF;
END $$;

-- Step 2: Verify all tenants have subscriptions
DO $$
DECLARE
    missing_count INT;
BEGIN
    SELECT COUNT(*) INTO missing_count
    FROM tenants t
    WHERE t.status = 'ACTIVE'
      AND NOT EXISTS (
          SELECT 1 FROM subscriptions s WHERE s.tenant_id = t.tenant_id
      );

    IF missing_count > 0 THEN
        RAISE EXCEPTION 'Cannot proceed: % active tenants without subscription', missing_count;
    END IF;
END $$;

-- Step 3: Archive tenant_subscription data (optional - for audit trail)
CREATE TABLE IF NOT EXISTS tenant_subscription_archive AS
SELECT *, now() as archived_at FROM tenant_subscription;

-- Step 4: Drop RLS policies on tenant_subscription
DROP POLICY IF EXISTS tenant_subscription_read ON tenant_subscription;
DROP POLICY IF EXISTS tenant_subscription_service_read ON tenant_subscription;

-- Step 5: Drop the table
DROP TABLE IF EXISTS tenant_subscription CASCADE;

-- Step 6: Remove any leftover functions that reference tenant_subscription
-- (Check for any functions and drop them)

-- Step 7: Log the migration
INSERT INTO subscription_audit (tenant_id, event_type, actor_type, actor_id, details)
SELECT DISTINCT tenant_id, 'SCHEMA_MIGRATION', 'system', 'migration-032',
       '{"action": "removed_tenant_subscription_table", "archived": true}'::jsonb
FROM subscriptions
LIMIT 1;

-- Step 8: Vacuum to reclaim space
VACUUM ANALYZE subscriptions;
VACUUM ANALYZE device_registry;
```

## 2. Backend Cleanup

Search for and remove any remaining references to `tenant_subscription`:

### services/ui_iot/services/subscription.py

Remove any functions that still reference `tenant_subscription`:

```python
# REMOVE these functions if they exist:
# - get_tenant_subscription() - replaced by get_tenant_subscriptions()
# - check_tenant_limit() - replaced by check_subscription_limit()
# - Any function with "tenant_subscription" in query

# KEEP these (multi-subscription versions):
# - create_subscription()
# - get_tenant_subscriptions()
# - check_subscription_limit()
# - assign_device_to_subscription()
# - check_device_access()
# - create_device_on_subscription()
```

### services/ui_iot/routes/customer.py

Remove old single-subscription endpoint:

```python
# REMOVE if exists:
# @router.get("/subscription")  # Old single subscription endpoint
# def get_subscription(): ...

# KEEP these (multi-subscription versions):
# @router.get("/subscriptions")
# @router.get("/subscriptions/{subscription_id}")
# @router.get("/subscription/audit")
# @router.post("/subscription/renew")
```

### services/ui_iot/routes/operator.py

Remove old tenant subscription management:

```python
# REMOVE if exists:
# @router.post("/tenants/{tenant_id}/subscription")  # Old single-subscription create
# @router.patch("/tenants/{tenant_id}/subscription")  # Old single-subscription update

# KEEP these (multi-subscription versions):
# @router.post("/subscriptions")
# @router.get("/subscriptions")
# @router.get("/subscriptions/{subscription_id}")
# @router.patch("/subscriptions/{subscription_id}")
# @router.post("/devices/{device_id}/subscription")
```

## 3. Frontend Cleanup

Search for and remove any UI components still using old endpoints:

```bash
# Search for old endpoint references
grep -r "subscription" frontend/src --include="*.tsx" --include="*.ts" | grep -v "subscriptions"
```

Remove or update:
- Any component fetching `/customer/subscription` (singular)
- Any component fetching `/operator/tenants/{id}/subscription`

## 4. Verification Script

Run after migration to verify cleanup:

```bash
# Check no references to tenant_subscription in code
grep -r "tenant_subscription" services/ frontend/src --include="*.py" --include="*.tsx" --include="*.ts"

# Check table is gone
docker compose -f compose/docker-compose.yml exec postgres psql -U iot -d iotcloud -c "
  SELECT EXISTS (
    SELECT FROM information_schema.tables
    WHERE table_name = 'tenant_subscription'
  ) as table_exists;
"
# Should return: table_exists = false

# Check archive exists
docker compose -f compose/docker-compose.yml exec postgres psql -U iot -d iotcloud -c "
  SELECT COUNT(*) as archived_records FROM tenant_subscription_archive;
"

# Verify subscription counts
docker compose -f compose/docker-compose.yml exec postgres psql -U iot -d iotcloud -c "
  SELECT
    (SELECT COUNT(*) FROM subscriptions) as total_subscriptions,
    (SELECT COUNT(*) FROM subscriptions WHERE subscription_type = 'MAIN') as main_subscriptions,
    (SELECT COUNT(DISTINCT tenant_id) FROM subscriptions) as tenants_with_subscriptions,
    (SELECT COUNT(*) FROM tenants WHERE status = 'ACTIVE') as active_tenants
"
```

## 5. Rollback (if needed)

```sql
-- Restore from archive
CREATE TABLE tenant_subscription AS
SELECT
    tenant_id, device_limit, active_device_count, term_start, term_end,
    plan_id, status, grace_end, created_at, updated_at
FROM tenant_subscription_archive;

-- Re-add primary key
ALTER TABLE tenant_subscription ADD PRIMARY KEY (tenant_id);

-- Re-enable RLS
ALTER TABLE tenant_subscription ENABLE ROW LEVEL SECURITY;

CREATE POLICY tenant_subscription_read ON tenant_subscription
    FOR SELECT USING (tenant_id = current_setting('app.tenant_id', true));
```

## Pre-Migration Checklist

- [ ] Phase 32 deployed for at least 1 week
- [ ] All E2E tests passing
- [ ] No errors referencing tenant_subscription in logs
- [ ] Database backup taken
- [ ] Downtime window scheduled (optional, can be done live)
- [ ] Rollback plan tested

## Post-Migration Checklist

- [ ] Migration ran without errors
- [ ] Archive table created with data
- [ ] No orphaned devices
- [ ] All tenants have subscriptions
- [ ] UI loads correctly
- [ ] Ingest working
- [ ] API endpoints responding
- [ ] Code search shows no tenant_subscription references
