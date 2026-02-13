-- ============================================
-- Migration: 050_cleanup_test_data.sql
-- Purpose: Remove all test data for fresh start
-- WARNING: This is destructive! Backup first!
-- ============================================

BEGIN;

-- Disable triggers temporarily for faster cleanup
SET session_replication_role = replica;

-- ============================================
-- 1. TimescaleDB Hypertables (drop chunks)
-- ============================================

DO $$
BEGIN
    PERFORM drop_chunks('telemetry', older_than => now() + interval '1 day');
    RAISE NOTICE 'Cleaned telemetry hypertable';
EXCEPTION WHEN OTHERS THEN
    RAISE NOTICE 'telemetry cleanup skipped: %', SQLERRM;
END $$;

DO $$
BEGIN
    PERFORM drop_chunks('device_state', older_than => now() + interval '1 day');
    RAISE NOTICE 'Cleaned device_state hypertable';
EXCEPTION WHEN OTHERS THEN
    BEGIN
        TRUNCATE TABLE device_state CASCADE;
        RAISE NOTICE 'Cleaned device_state via truncate fallback';
    EXCEPTION WHEN OTHERS THEN
        RAISE NOTICE 'device_state cleanup skipped: %', SQLERRM;
    END;
END $$;

DO $$
BEGIN
    PERFORM drop_chunks('audit_log', older_than => now() + interval '1 day');
    RAISE NOTICE 'Cleaned audit_log hypertable';
EXCEPTION WHEN OTHERS THEN
    BEGIN
        TRUNCATE TABLE audit_log CASCADE;
        RAISE NOTICE 'Cleaned audit_log via truncate fallback';
    EXCEPTION WHEN OTHERS THEN
        RAISE NOTICE 'audit_log cleanup skipped: %', SQLERRM;
    END;
END $$;

-- ============================================
-- 2. Activity and Audit Logs
-- ============================================

TRUNCATE TABLE operator_audit_log CASCADE;
TRUNCATE TABLE subscription_audit CASCADE;
TRUNCATE TABLE subscription_notifications CASCADE;

-- ============================================
-- 3. Alerts and Notifications
-- ============================================

TRUNCATE TABLE fleet_alert CASCADE;
TRUNCATE TABLE alert_rules CASCADE;

-- ============================================
-- 4. Device Data
-- ============================================

DELETE FROM device_tags;
DELETE FROM device_registry;

-- Optional: device_extended_attributes if it exists
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'device_extended_attributes') THEN
        DELETE FROM device_extended_attributes;
        RAISE NOTICE 'Cleaned device_extended_attributes';
    END IF;
END $$;

-- ============================================
-- 5. Sites (if table exists)
-- ============================================

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'sites') THEN
        DELETE FROM sites;
        RAISE NOTICE 'Cleaned sites';
    END IF;
END $$;

-- ============================================
-- 6. Subscriptions
-- ============================================

DELETE FROM subscriptions;

-- ============================================
-- 7. Tenants (full reset)
-- ============================================

DELETE FROM tenants;

-- ============================================
-- 8. Quarantine / ingest rejects
-- ============================================

TRUNCATE TABLE quarantine_events CASCADE;
TRUNCATE TABLE quarantine_counters_minute CASCADE;

-- ============================================
-- 9. Reset sequences (optional fresh IDs)
-- ============================================

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
EXCEPTION WHEN OTHERS THEN
    RAISE NOTICE 'Sequence reset skipped: %', SQLERRM;
END $$;

-- Re-enable triggers
SET session_replication_role = DEFAULT;

COMMIT;

-- Run VACUUM manually later if needed:
-- VACUUM ANALYZE;
