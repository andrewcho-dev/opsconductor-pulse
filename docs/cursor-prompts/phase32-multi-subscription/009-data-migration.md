# 009: Data Migration to Multi-Subscription Schema

## Task

Migrate existing data from the old `tenant_subscription` model to the new `subscriptions` model.

## File to Create

`db/migrations/031_migrate_subscription_data.sql`

## Migration Steps

### 1. Create MAIN subscription for each tenant with existing subscription

```sql
-- Migrate existing tenant_subscription records to new subscriptions table
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
    created_at,
    created_by
)
SELECT
    'SUB-MIGRATED-' || tenant_id,  -- Temporary ID format for migrated records
    tenant_id,
    'MAIN',
    NULL,
    device_limit,
    active_device_count,
    COALESCE(term_start, created_at),
    COALESCE(term_end, created_at + interval '1 year'),
    status,
    grace_end,
    plan_id,
    'Migrated from legacy subscription',
    created_at,
    'migration'
FROM tenant_subscription
ON CONFLICT (subscription_id) DO NOTHING;
```

### 2. Assign all existing devices to their tenant's MAIN subscription

```sql
-- Update devices to reference their tenant's MAIN subscription
UPDATE device_registry dr
SET subscription_id = s.subscription_id
FROM subscriptions s
WHERE dr.tenant_id = s.tenant_id
  AND s.subscription_type = 'MAIN'
  AND dr.subscription_id IS NULL;
```

### 3. Recalculate active_device_count for accuracy

```sql
-- Recalculate device counts from actual device_registry
UPDATE subscriptions s
SET active_device_count = (
    SELECT COUNT(*)
    FROM device_registry dr
    WHERE dr.subscription_id = s.subscription_id
      AND dr.status = 'ACTIVE'
);
```

### 4. Create subscriptions for tenants without one

Some tenants might have devices but no subscription record. Create default subscriptions:

```sql
-- Find tenants with devices but no subscription
INSERT INTO subscriptions (
    subscription_id,
    tenant_id,
    subscription_type,
    device_limit,
    active_device_count,
    term_start,
    term_end,
    status,
    description,
    created_by
)
SELECT
    'SUB-DEFAULT-' || t.tenant_id,
    t.tenant_id,
    'MAIN',
    1000,  -- Generous default
    0,
    now(),
    now() + interval '1 year',
    'ACTIVE',
    'Default subscription created during migration',
    'migration'
FROM tenants t
WHERE t.status = 'ACTIVE'
  AND NOT EXISTS (
      SELECT 1 FROM subscriptions s WHERE s.tenant_id = t.tenant_id
  )
ON CONFLICT (subscription_id) DO NOTHING;

-- Assign orphaned devices to default subscriptions
UPDATE device_registry dr
SET subscription_id = s.subscription_id
FROM subscriptions s
WHERE dr.tenant_id = s.tenant_id
  AND s.subscription_type = 'MAIN'
  AND dr.subscription_id IS NULL;

-- Update counts again
UPDATE subscriptions s
SET active_device_count = (
    SELECT COUNT(*)
    FROM device_registry dr
    WHERE dr.subscription_id = s.subscription_id
      AND dr.status = 'ACTIVE'
);
```

### 5. Verify migration

```sql
-- Check for devices without subscriptions (should be 0)
SELECT COUNT(*) as orphaned_devices
FROM device_registry
WHERE subscription_id IS NULL
  AND status = 'ACTIVE';

-- Check subscription counts match device counts
SELECT
    s.subscription_id,
    s.active_device_count as recorded_count,
    COUNT(dr.device_id) as actual_count,
    s.active_device_count - COUNT(dr.device_id) as difference
FROM subscriptions s
LEFT JOIN device_registry dr ON dr.subscription_id = s.subscription_id AND dr.status = 'ACTIVE'
GROUP BY s.subscription_id, s.active_device_count
HAVING s.active_device_count != COUNT(dr.device_id);

-- List subscriptions by tenant
SELECT
    s.tenant_id,
    t.name as tenant_name,
    s.subscription_id,
    s.subscription_type,
    s.device_limit,
    s.active_device_count,
    s.status
FROM subscriptions s
JOIN tenants t ON t.tenant_id = s.tenant_id
ORDER BY s.tenant_id, s.subscription_type;
```

### 6. Add audit log entries for migration

```sql
-- Log the migration event
INSERT INTO subscription_audit (
    tenant_id,
    event_type,
    actor_type,
    actor_id,
    details
)
SELECT
    tenant_id,
    'DATA_MIGRATED',
    'system',
    'migration-script',
    json_build_object(
        'subscription_id', subscription_id,
        'from_schema', 'tenant_subscription',
        'to_schema', 'subscriptions',
        'device_count', active_device_count
    )
FROM subscriptions
WHERE description LIKE '%migration%';
```

### 7. Rename subscription IDs to proper format (optional)

```sql
-- Generate proper subscription IDs for migrated records
-- This is optional but recommended for consistency

DO $$
DECLARE
    r RECORD;
    new_id TEXT;
BEGIN
    FOR r IN
        SELECT subscription_id, tenant_id
        FROM subscriptions
        WHERE subscription_id LIKE 'SUB-MIGRATED-%'
           OR subscription_id LIKE 'SUB-DEFAULT-%'
    LOOP
        new_id := 'SUB-' || to_char(now(), 'YYYYMMDD') || '-' ||
                  LPAD(nextval('subscription_id_seq')::TEXT, 5, '0');

        -- Update subscriptions table
        UPDATE subscriptions SET subscription_id = new_id WHERE subscription_id = r.subscription_id;

        -- Update device_registry references
        UPDATE device_registry SET subscription_id = new_id WHERE subscription_id = r.subscription_id;

        -- Update parent references
        UPDATE subscriptions SET parent_subscription_id = new_id WHERE parent_subscription_id = r.subscription_id;

        -- Update audit log
        UPDATE subscription_audit
        SET details = jsonb_set(details, '{old_subscription_id}', to_jsonb(r.subscription_id))
        WHERE tenant_id = r.tenant_id
          AND event_type = 'DATA_MIGRATED';
    END LOOP;
END $$;
```

## Running the Migration

```bash
# Backup first!
docker compose exec postgres pg_dump -U iot iotcloud > backup_before_migration.sql

# Run the migration
docker compose exec postgres psql -U iot -d iotcloud \
  -f /path/to/031_migrate_subscription_data.sql

# Verify
docker compose exec postgres psql -U iot -d iotcloud -c "
  SELECT
    (SELECT COUNT(*) FROM subscriptions) as total_subscriptions,
    (SELECT COUNT(*) FROM device_registry WHERE subscription_id IS NOT NULL) as assigned_devices,
    (SELECT COUNT(*) FROM device_registry WHERE subscription_id IS NULL AND status = 'ACTIVE') as orphaned_devices
"
```

## Rollback (if needed)

```sql
-- Clear new subscriptions table
DELETE FROM subscriptions;

-- Clear subscription_id from devices
UPDATE device_registry SET subscription_id = NULL;

-- The old tenant_subscription table is still intact
```

## After Migration

1. Test all APIs work with new schema
2. Run E2E tests
3. Mark `tenant_subscription` as deprecated
4. Plan removal of `tenant_subscription` in future migration
