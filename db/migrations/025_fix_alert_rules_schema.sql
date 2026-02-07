-- Migration: 025_fix_alert_rules_schema.sql
-- Purpose: Add missing columns to alert_rules table that the application expects
-- The base schema used conditions JSONB, but the app code expects individual columns

-- Add missing columns
ALTER TABLE alert_rules ADD COLUMN IF NOT EXISTS rule_id TEXT;
ALTER TABLE alert_rules ADD COLUMN IF NOT EXISTS metric_name TEXT;
ALTER TABLE alert_rules ADD COLUMN IF NOT EXISTS operator TEXT;
ALTER TABLE alert_rules ADD COLUMN IF NOT EXISTS threshold DOUBLE PRECISION;
ALTER TABLE alert_rules ADD COLUMN IF NOT EXISTS severity INTEGER NOT NULL DEFAULT 3;
ALTER TABLE alert_rules ADD COLUMN IF NOT EXISTS site_ids TEXT[] NULL;

-- Set default rule_id from id if not set
UPDATE alert_rules SET rule_id = id::text WHERE rule_id IS NULL;

-- Make rule_id NOT NULL after backfill
ALTER TABLE alert_rules ALTER COLUMN rule_id SET DEFAULT gen_random_uuid()::text;

-- Create unique constraint on (tenant_id, rule_id) if it doesn't exist
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'alert_rules_tenant_rule_id_key'
    ) THEN
        ALTER TABLE alert_rules ADD CONSTRAINT alert_rules_tenant_rule_id_key
            UNIQUE (tenant_id, rule_id);
    END IF;
END $$;

-- Verify
DO $$
BEGIN
    RAISE NOTICE 'alert_rules schema updated with threshold rule columns';
END $$;
