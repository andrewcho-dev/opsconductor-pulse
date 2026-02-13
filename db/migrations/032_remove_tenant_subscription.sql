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
