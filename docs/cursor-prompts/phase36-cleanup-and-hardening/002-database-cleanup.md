# 002: Database Cleanup

## Task

Remove all test data from the database while preserving schema and system configuration.

## Prerequisites

- Simulators stopped (001-stop-simulators.md)
- Database backup if needed

## Backup First (Optional)

```bash
# Create backup before cleanup
docker compose exec postgres pg_dump -U iot iotcloud > backup_before_cleanup_$(date +%Y%m%d_%H%M%S).sql
```

## Cleanup Migration

**File:** `db/migrations/050_cleanup_test_data.sql`

```sql
-- ============================================
-- Migration: 050_cleanup_test_data.sql
-- Purpose: Remove all test data for fresh start
-- WARNING: This is destructive! Backup first!
-- ============================================

BEGIN;

-- Disable triggers temporarily for faster cleanup
SET session_replication_role = replica;

-- ============================================
-- 1. TimescaleDB Hypertables (special handling)
-- ============================================

-- Telemetry data - use TimescaleDB drop_chunks for efficiency
-- This is faster than DELETE for hypertables
DO $$
BEGIN
    -- Drop all chunks (deletes all data but keeps table structure)
    PERFORM drop_chunks('device_telemetry', older_than => now() + interval '1 day');
    RAISE NOTICE 'Cleaned device_telemetry hypertable';
EXCEPTION WHEN OTHERS THEN
    RAISE NOTICE 'device_telemetry cleanup skipped: %', SQLERRM;
END $$;

DO $$
BEGIN
    PERFORM drop_chunks('device_state', older_than => now() + interval '1 day');
    RAISE NOTICE 'Cleaned device_state hypertable';
EXCEPTION WHEN OTHERS THEN
    RAISE NOTICE 'device_state cleanup skipped: %', SQLERRM;
END $$;

-- ============================================
-- 2. Activity and Audit Logs
-- ============================================

-- Truncate is faster than DELETE for large tables
TRUNCATE TABLE activity_log CASCADE;
TRUNCATE TABLE operator_audit_log CASCADE;
TRUNCATE TABLE subscription_audit CASCADE;

-- If activity_log is a hypertable:
DO $$
BEGIN
    PERFORM drop_chunks('activity_log', older_than => now() + interval '1 day');
EXCEPTION WHEN undefined_table THEN
    -- Not a hypertable, already truncated above
    NULL;
END $$;

-- ============================================
-- 3. Alerts and Notifications
-- ============================================

TRUNCATE TABLE fleet_alert CASCADE;
TRUNCATE TABLE alert_rules CASCADE;
TRUNCATE TABLE subscription_notifications CASCADE;

-- ============================================
-- 4. Device Data
-- ============================================

-- Delete devices (this cascades to related tables)
DELETE FROM device_registry;

-- Clean up any orphaned device attributes
DELETE FROM device_extended_attributes WHERE device_id NOT IN (SELECT device_id FROM device_registry);

-- ============================================
-- 5. Sites
-- ============================================

DELETE FROM sites;

-- ============================================
-- 6. Subscriptions
-- ============================================

DELETE FROM subscriptions;
DELETE FROM tenant_subscription;

-- ============================================
-- 7. Tenants (if starting completely fresh)
-- ============================================

-- WARNING: This removes all tenants!
-- Comment out if you want to keep tenant definitions
DELETE FROM tenants;

-- ============================================
-- 8. Keycloak-related Data
-- ============================================

-- If there's any cached user data, clean it
-- (Keycloak is the source of truth, this is just cache)

-- ============================================
-- 9. Reset Sequences
-- ============================================

-- Reset auto-increment sequences to 1
DO $$
DECLARE
    seq_record RECORD;
BEGIN
    FOR seq_record IN
        SELECT schemaname, sequencename
        FROM pg_sequences
        WHERE schemaname = 'public'
    LOOP
        EXECUTE format('ALTER SEQUENCE %I.%I RESTART WITH 1',
            seq_record.schemaname, seq_record.sequencename);
    END LOOP;
END $$;

-- ============================================
-- 10. Vacuum and Analyze
-- ============================================

-- Re-enable triggers
SET session_replication_role = DEFAULT;

COMMIT;

-- Run VACUUM outside transaction
VACUUM ANALYZE;

-- ============================================
-- Verification
-- ============================================

DO $$
DECLARE
    row_counts TEXT := '';
    tbl RECORD;
BEGIN
    FOR tbl IN
        SELECT tablename FROM pg_tables
        WHERE schemaname = 'public'
        AND tablename NOT LIKE 'pg_%'
        AND tablename NOT LIKE '_timescaledb_%'
        ORDER BY tablename
    LOOP
        EXECUTE format('SELECT COUNT(*) FROM %I', tbl.tablename) INTO row_counts;
        RAISE NOTICE 'Table %: % rows', tbl.tablename, row_counts;
    END LOOP;
END $$;
```

## Run the Cleanup

```bash
# Apply the migration
docker compose exec postgres psql -U iot -d iotcloud -f /path/to/050_cleanup_test_data.sql

# Or run directly:
docker compose exec postgres psql -U iot -d iotcloud << 'EOF'
-- Paste the SQL above
EOF
```

## Quick Cleanup Commands

If you need immediate cleanup without a migration file:

```bash
# Connect to database
docker compose exec postgres psql -U iot -d iotcloud

# Then run:
```

```sql
-- Immediate cleanup (run in psql)
SET session_replication_role = replica;

TRUNCATE TABLE activity_log CASCADE;
TRUNCATE TABLE operator_audit_log CASCADE;
TRUNCATE TABLE subscription_audit CASCADE;
TRUNCATE TABLE fleet_alert CASCADE;
TRUNCATE TABLE subscription_notifications CASCADE;

DELETE FROM device_registry;
DELETE FROM sites;
DELETE FROM subscriptions;
DELETE FROM tenants;

SET session_replication_role = DEFAULT;
VACUUM ANALYZE;
```

## Verify Cleanup

```bash
# Check row counts
docker compose exec postgres psql -U iot -d iotcloud -c "
SELECT
    schemaname,
    relname as table_name,
    n_live_tup as row_count
FROM pg_stat_user_tables
WHERE schemaname = 'public'
ORDER BY n_live_tup DESC;
"

# Check disk usage
docker compose exec postgres psql -U iot -d iotcloud -c "
SELECT
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname || '.' || tablename)) as size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname || '.' || tablename) DESC
LIMIT 20;
"

# Expected: All tables should show 0 or near-0 rows
# Expected: Total database size should be minimal (under 100MB)
```

## Reclaim Disk Space

```bash
# Full vacuum to reclaim disk space
docker compose exec postgres psql -U iot -d iotcloud -c "VACUUM FULL;"

# Check database size after
docker compose exec postgres psql -U iot -d iotcloud -c "
SELECT pg_size_pretty(pg_database_size('iotcloud')) as database_size;
"
```

## TimescaleDB Specific Cleanup

If tables are hypertables, use this approach:

```sql
-- List all hypertables
SELECT hypertable_name FROM timescaledb_information.hypertables;

-- For each hypertable, drop all chunks
SELECT drop_chunks('device_telemetry', older_than => now() + interval '100 years');
SELECT drop_chunks('device_state', older_than => now() + interval '100 years');
SELECT drop_chunks('activity_log', older_than => now() + interval '100 years');

-- Verify chunks are gone
SELECT * FROM timescaledb_information.chunks;
```

## Files Modified

- `db/migrations/050_cleanup_test_data.sql` (NEW)
