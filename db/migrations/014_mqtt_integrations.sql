-- Add MQTT support to integrations table
-- Migration: 014_mqtt_integrations.sql

-- Ensure enum includes 'mqtt'
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_type WHERE typname = 'integration_type') THEN
        IF NOT EXISTS (
            SELECT 1
            FROM pg_enum
            WHERE enumlabel = 'mqtt'
              AND enumtypid = 'integration_type'::regtype
        ) THEN
            ALTER TYPE integration_type ADD VALUE 'mqtt';
        END IF;
    END IF;
END$$;

-- Update type constraint to include 'mqtt'
ALTER TABLE integrations DROP CONSTRAINT IF EXISTS integrations_type_check;
ALTER TABLE integrations ADD CONSTRAINT integrations_type_check
    CHECK (type::text IN ('webhook', 'snmp', 'email', 'mqtt'));

-- Add MQTT configuration columns
ALTER TABLE integrations ADD COLUMN IF NOT EXISTS mqtt_topic VARCHAR(512);
ALTER TABLE integrations ADD COLUMN IF NOT EXISTS mqtt_qos INTEGER DEFAULT 1;
ALTER TABLE integrations ADD COLUMN IF NOT EXISTS mqtt_retain BOOLEAN DEFAULT false;
ALTER TABLE integrations ADD COLUMN IF NOT EXISTS mqtt_config JSONB;

-- Add index for MQTT integrations
CREATE INDEX IF NOT EXISTS idx_integrations_mqtt
    ON integrations(tenant_id) WHERE type = 'mqtt';

-- Update config constraint to include MQTT requirements
DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'integration_type_config_check'
    ) THEN
        ALTER TABLE integrations DROP CONSTRAINT integration_type_config_check;
    END IF;
END$$;

ALTER TABLE integrations
ADD CONSTRAINT integration_type_config_check CHECK (
    (type::text = 'webhook' AND (config_json->>'url') IS NOT NULL) OR
    (type::text = 'snmp' AND snmp_host IS NOT NULL AND snmp_config IS NOT NULL) OR
    (type::text = 'email' AND email_config IS NOT NULL AND email_recipients IS NOT NULL) OR
    (type::text = 'mqtt' AND mqtt_topic IS NOT NULL)
);
