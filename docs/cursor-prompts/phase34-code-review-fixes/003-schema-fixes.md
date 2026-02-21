# 003: Database Schema Fixes

## Priority: HIGH

## Issues to Fix

### 1. Duplicate Migration Number 024

**Problem:** Two files have same migration number:
- `db/migrations/024_device_extended_attributes.sql`
- `db/migrations/024_fix_telemetry_compression.sql`

**Fix:** Rename one:
```bash
mv db/migrations/024_fix_telemetry_compression.sql db/migrations/034_fix_telemetry_compression.sql
```

---

### 2. device_registry Missing RLS

**File:** `db/migrations/004_enable_rls.sql`

**Problem:** device_registry not included in RLS policies, causing tenant isolation gap.

**Fix:** Create migration `db/migrations/035_device_registry_rls.sql`:
```sql
-- Enable RLS on device_registry
ALTER TABLE device_registry ENABLE ROW LEVEL SECURITY;

-- Policy for tenant read/write
CREATE POLICY device_registry_tenant_policy ON device_registry
    FOR ALL
    USING (tenant_id = current_setting('app.tenant_id', true))
    WITH CHECK (tenant_id = current_setting('app.tenant_id', true));

-- Policy for operator read-only
CREATE POLICY device_registry_operator_read ON device_registry
    FOR SELECT
    TO pulse_operator
    USING (true);

-- Policy for iot service (ingest needs full access)
CREATE POLICY device_registry_service ON device_registry
    FOR ALL
    TO iot
    USING (true)
    WITH CHECK (true);
```

---

### 3. delivery_jobs and quarantine_events Missing RLS

**Fix:** Add to same migration:
```sql
-- Enable RLS on delivery_jobs
ALTER TABLE delivery_jobs ENABLE ROW LEVEL SECURITY;

CREATE POLICY delivery_jobs_tenant_policy ON delivery_jobs
    FOR ALL
    USING (tenant_id = current_setting('app.tenant_id', true));

CREATE POLICY delivery_jobs_service ON delivery_jobs
    FOR ALL
    TO iot
    USING (true);

-- Enable RLS on quarantine_events
ALTER TABLE quarantine_events ENABLE ROW LEVEL SECURITY;

CREATE POLICY quarantine_events_tenant_policy ON quarantine_events
    FOR SELECT
    USING (tenant_id = current_setting('app.tenant_id', true));

CREATE POLICY quarantine_events_service ON quarantine_events
    FOR ALL
    TO iot
    USING (true);
```

---

### 4. Missing Foreign Keys

**Fix:** Create migration `db/migrations/036_add_foreign_keys.sql`:
```sql
-- Add FK from device_registry to tenants
ALTER TABLE device_registry
ADD CONSTRAINT fk_device_registry_tenant
FOREIGN KEY (tenant_id) REFERENCES tenants(tenant_id)
ON DELETE CASCADE;

-- Add FK from device_state to tenants
ALTER TABLE device_state
ADD CONSTRAINT fk_device_state_tenant
FOREIGN KEY (tenant_id) REFERENCES tenants(tenant_id)
ON DELETE CASCADE;

-- Add FK from alert_rules to tenants
ALTER TABLE alert_rules
ADD CONSTRAINT fk_alert_rules_tenant
FOREIGN KEY (tenant_id) REFERENCES tenants(tenant_id)
ON DELETE CASCADE;

-- Add FK from fleet_alert to tenants
ALTER TABLE fleet_alert
ADD CONSTRAINT fk_fleet_alert_tenant
FOREIGN KEY (tenant_id) REFERENCES tenants(tenant_id)
ON DELETE CASCADE;

-- Add FK from integration_routes to tenants
ALTER TABLE integration_routes
ADD CONSTRAINT fk_integration_routes_tenant
FOREIGN KEY (tenant_id) REFERENCES tenants(tenant_id)
ON DELETE CASCADE;

-- Add FK from integrations to tenants
ALTER TABLE integrations
ADD CONSTRAINT fk_integrations_tenant
FOREIGN KEY (tenant_id) REFERENCES tenants(tenant_id)
ON DELETE CASCADE;
```

---

### 5. Missing Indexes

**Fix:** Create migration `db/migrations/037_add_missing_indexes.sql`:
```sql
-- Single-column tenant_id index on device_registry for direct tenant lookups
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_device_registry_tenant
ON device_registry(tenant_id);

-- Composite index for tenant + created_at on fleet_alert
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_fleet_alert_tenant_created
ON fleet_alert(tenant_id, created_at DESC);

-- GIN index for telemetry metrics JSONB queries
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_telemetry_metrics_gin
ON telemetry USING GIN (metrics);

-- Index for delivery_jobs tenant lookup
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_delivery_jobs_tenant
ON delivery_jobs(tenant_id);

-- Index for subscription lookups by tenant
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_subscriptions_tenant_type
ON subscriptions(tenant_id, subscription_type);
```

---

### 6. Missing CHECK Constraints

**Fix:** Create migration `db/migrations/038_add_check_constraints.sql`:
```sql
-- device_state status constraint
ALTER TABLE device_state
ADD CONSTRAINT chk_device_state_status
CHECK (status IN ('ONLINE', 'STALE', 'OFFLINE'));

-- fleet_alert status constraint
ALTER TABLE fleet_alert
ADD CONSTRAINT chk_fleet_alert_status
CHECK (status IN ('OPEN', 'ACKNOWLEDGED', 'CLOSED'));

-- device_registry status constraint
ALTER TABLE device_registry
ADD CONSTRAINT chk_device_registry_status
CHECK (status IN ('ACTIVE', 'INACTIVE', 'SUSPENDED'));

-- integration_routes enabled must be boolean (already is, but explicit)
-- No change needed if using BOOLEAN type

-- delivery_jobs status constraint
ALTER TABLE delivery_jobs
ADD CONSTRAINT chk_delivery_jobs_status
CHECK (status IN ('pending', 'processing', 'completed', 'failed', 'dead'));
```

---

### 7. Clean Up Deprecated raw_events RLS

**Fix:** Create migration `db/migrations/039_cleanup_deprecated_policies.sql`:
```sql
-- Drop RLS policies that reference renamed raw_events table
DROP POLICY IF EXISTS raw_events_read ON raw_events;
DROP POLICY IF EXISTS raw_events_write ON raw_events;

-- If _deprecated_raw_events exists, ensure it has no active policies
DROP POLICY IF EXISTS raw_events_read ON _deprecated_raw_events;
DROP POLICY IF EXISTS raw_events_write ON _deprecated_raw_events;

-- Drop the deprecated table if it's empty and not needed
-- (Uncomment after verifying no dependencies)
-- DROP TABLE IF EXISTS _deprecated_raw_events;
```

---

### 8. Fix alert_rules Dual Schema

**Problem:** 000_base_schema.sql and 025_fix_alert_rules_schema.sql define conflicting columns.

**Fix:** Determine canonical schema. If using individual columns (current code):
```sql
-- Verify current schema matches code expectations
-- In db/migrations/040_verify_alert_rules_schema.sql

-- Ensure required columns exist
DO $$
BEGIN
    -- Check for required columns
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'alert_rules' AND column_name = 'metric_name'
    ) THEN
        ALTER TABLE alert_rules ADD COLUMN metric_name TEXT;
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'alert_rules' AND column_name = 'operator'
    ) THEN
        ALTER TABLE alert_rules ADD COLUMN operator TEXT;
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'alert_rules' AND column_name = 'threshold'
    ) THEN
        ALTER TABLE alert_rules ADD COLUMN threshold NUMERIC;
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'alert_rules' AND column_name = 'severity'
    ) THEN
        ALTER TABLE alert_rules ADD COLUMN severity TEXT DEFAULT 'medium';
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'alert_rules' AND column_name = 'site_ids'
    ) THEN
        ALTER TABLE alert_rules ADD COLUMN site_ids TEXT[];
    END IF;
END $$;

-- Add constraints
ALTER TABLE alert_rules
ADD CONSTRAINT chk_alert_rules_operator
CHECK (operator IN ('>', '<', '>=', '<=', '==', '!='));

ALTER TABLE alert_rules
ADD CONSTRAINT chk_alert_rules_severity
CHECK (severity IN ('critical', 'high', 'medium', 'low', 'info'));
```

---

### 9. Fix device_registry.provisioned_at Reference

**Problem:** Migration 018 references `MIN(provisioned_at)` but column doesn't exist.

**Fix:** Either add the column or fix the migration:

**Option A - Add column:**
```sql
-- In new migration
ALTER TABLE device_registry
ADD COLUMN IF NOT EXISTS provisioned_at TIMESTAMPTZ DEFAULT now();

-- Backfill from created_at
UPDATE device_registry
SET provisioned_at = created_at
WHERE provisioned_at IS NULL;
```

**Option B - Fix migration 018:**
Change `MIN(provisioned_at)` to `MIN(created_at)` in the migration file.

---

## Migration Execution Order

Run in this order:
1. `034_fix_telemetry_compression.sql` (renumbered)
2. `035_device_registry_rls.sql`
3. `036_add_foreign_keys.sql`
4. `037_add_missing_indexes.sql`
5. `038_add_check_constraints.sql`
6. `039_cleanup_deprecated_policies.sql`
7. `040_verify_alert_rules_schema.sql`

---

## Verification

```bash
# Check RLS is enabled
psql -c "SELECT tablename, rowsecurity FROM pg_tables WHERE schemaname = 'public' AND tablename IN ('device_registry', 'delivery_jobs', 'quarantine_events')"
# All should show rowsecurity = true

# Check foreign keys
psql -c "SELECT conname, conrelid::regclass, confrelid::regclass FROM pg_constraint WHERE contype = 'f' AND conrelid::regclass::text LIKE '%device%'"

# Check indexes
psql -c "SELECT indexname FROM pg_indexes WHERE tablename = 'device_registry'"

# Test RLS enforcement
psql -c "SET app.tenant_id = 'tenant-a'; SELECT COUNT(*) FROM device_registry;"
psql -c "SET app.tenant_id = 'tenant-b'; SELECT COUNT(*) FROM device_registry;"
# Counts should differ based on tenant data
```

## Files Changed

- `db/migrations/024_fix_telemetry_compression.sql` → renamed to `034_...`
- `db/migrations/035_device_registry_rls.sql` (NEW)
- `db/migrations/036_add_foreign_keys.sql` (NEW)
- `db/migrations/037_add_missing_indexes.sql` (NEW)
- `db/migrations/038_add_check_constraints.sql` (NEW)
- `db/migrations/039_cleanup_deprecated_policies.sql` (NEW)
- `db/migrations/040_verify_alert_rules_schema.sql` (NEW)
