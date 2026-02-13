-- Phase 32: Data migration from tenant_subscription to subscriptions
-- IMPORTANT: Run this AFTER deploying all Phase 32 code changes.

-- 1. Create MAIN subscription for each tenant with existing tenant_subscription
INSERT INTO subscriptions (
  subscription_id,
  tenant_id,
  subscription_type,
  parent_subscription_id,
  device_limit,
  active_device_count,
  term_start,
  term_end,
  status,
  grace_end,
  plan_id,
  description,
  created_by
)
SELECT
  'SUB-MIGRATED-' || ts.tenant_id AS subscription_id,
  ts.tenant_id,
  'MAIN' AS subscription_type,
  NULL AS parent_subscription_id,
  ts.device_limit,
  ts.active_device_count,
  ts.term_start,
  ts.term_end,
  ts.status,
  ts.grace_end,
  ts.plan_id,
  'Migrated from legacy subscription' AS description,
  'migration' AS created_by
FROM tenant_subscription ts
WHERE NOT EXISTS (
  SELECT 1 FROM subscriptions s WHERE s.tenant_id = ts.tenant_id
);

-- 2. Assign all existing devices to their tenant's MAIN subscription
UPDATE device_registry dr
SET subscription_id = s.subscription_id
FROM subscriptions s
WHERE dr.tenant_id = s.tenant_id
  AND s.subscription_type = 'MAIN'
  AND dr.subscription_id IS NULL;

-- 3. Recalculate active_device_count from actual device_registry counts
UPDATE subscriptions s
SET active_device_count = COALESCE(agg.device_count, 0),
    updated_at = now()
FROM (
  SELECT subscription_id, COUNT(*) AS device_count
  FROM device_registry
  WHERE status = 'ACTIVE' AND subscription_id IS NOT NULL
  GROUP BY subscription_id
) agg
WHERE s.subscription_id = agg.subscription_id;

-- 4. Create default subscriptions for tenants without one
INSERT INTO subscriptions (
  subscription_id,
  tenant_id,
  subscription_type,
  parent_subscription_id,
  device_limit,
  active_device_count,
  term_start,
  term_end,
  status,
  description,
  created_by
)
SELECT
  'SUB-DEFAULT-' || t.tenant_id AS subscription_id,
  t.tenant_id,
  'MAIN' AS subscription_type,
  NULL AS parent_subscription_id,
  1000 AS device_limit,
  0 AS active_device_count,
  now() AS term_start,
  now() + interval '1 year' AS term_end,
  'ACTIVE' AS status,
  'Default subscription created during migration' AS description,
  'migration' AS created_by
FROM tenants t
WHERE NOT EXISTS (
  SELECT 1 FROM subscriptions s WHERE s.tenant_id = t.tenant_id
);

-- Assign any orphaned devices to tenant MAIN subscription
UPDATE device_registry dr
SET subscription_id = s.subscription_id
FROM subscriptions s
WHERE dr.tenant_id = s.tenant_id
  AND s.subscription_type = 'MAIN'
  AND dr.subscription_id IS NULL;

-- Recalculate counts after orphan assignment
UPDATE subscriptions s
SET active_device_count = COALESCE(agg.device_count, 0),
    updated_at = now()
FROM (
  SELECT subscription_id, COUNT(*) AS device_count
  FROM device_registry
  WHERE status = 'ACTIVE' AND subscription_id IS NOT NULL
  GROUP BY subscription_id
) agg
WHERE s.subscription_id = agg.subscription_id;

-- 5. Verification queries (SELECT only)
-- Count orphaned devices (should be 0)
-- SELECT COUNT(*) FROM device_registry WHERE subscription_id IS NULL AND status = 'ACTIVE';
-- Check subscription counts match device counts
-- SELECT s.subscription_id, s.active_device_count,
--        COALESCE(c.cnt, 0) AS actual_count
-- FROM subscriptions s
-- LEFT JOIN (
--   SELECT subscription_id, COUNT(*) AS cnt
--   FROM device_registry
--   WHERE status = 'ACTIVE'
--   GROUP BY subscription_id
-- ) c ON c.subscription_id = s.subscription_id;
-- List subscriptions by tenant
-- SELECT tenant_id, subscription_id, subscription_type, status FROM subscriptions ORDER BY tenant_id;

-- 6. Add audit log entries for migration
INSERT INTO subscription_audit
  (tenant_id, event_type, actor_type, actor_id, new_state, details)
SELECT
  s.tenant_id,
  'DATA_MIGRATED',
  'system',
  'migration-script',
  to_jsonb(s),
  jsonb_build_object('subscription_id', s.subscription_id)
FROM subscriptions s
WHERE s.created_by = 'migration';

-- 7. (Optional) Rename subscription IDs to proper format
-- DO $$
-- DECLARE
--   rec RECORD;
--   new_id TEXT;
-- BEGIN
--   FOR rec IN
--     SELECT subscription_id
--     FROM subscriptions
--     WHERE subscription_id LIKE 'SUB-MIGRATED-%'
--        OR subscription_id LIKE 'SUB-DEFAULT-%'
--   LOOP
--     new_id := generate_subscription_id();
--     UPDATE subscriptions
--     SET subscription_id = new_id
--     WHERE subscription_id = rec.subscription_id;
--     UPDATE device_registry
--     SET subscription_id = new_id
--     WHERE subscription_id = rec.subscription_id;
--     UPDATE subscriptions
--     SET parent_subscription_id = new_id
--     WHERE parent_subscription_id = rec.subscription_id;
--   END LOOP;
-- END $$;

-- Rollback (manual):
-- DELETE FROM subscriptions;
-- UPDATE device_registry SET subscription_id = NULL;
