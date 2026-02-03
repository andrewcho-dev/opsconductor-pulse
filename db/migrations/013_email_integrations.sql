-- Add email support to integrations table
-- Migration: 013_email_integrations.sql

-- Ensure enum includes 'email'
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_type WHERE typname = 'integration_type') THEN
        IF NOT EXISTS (
            SELECT 1
            FROM pg_enum
            WHERE enumlabel = 'email'
              AND enumtypid = 'integration_type'::regtype
        ) THEN
            ALTER TYPE integration_type ADD VALUE 'email';
        END IF;
    END IF;
END$$;

-- Update type constraint to include 'email'
ALTER TABLE integrations DROP CONSTRAINT IF EXISTS integrations_type_check;
ALTER TABLE integrations ADD CONSTRAINT integrations_type_check
    CHECK (type IN ('webhook', 'snmp', 'email'));

-- Add email configuration columns
ALTER TABLE integrations ADD COLUMN IF NOT EXISTS email_config JSONB;
-- email_config structure:
-- {
--   "smtp_host": "smtp.example.com",
--   "smtp_port": 587,
--   "smtp_user": "user@example.com",
--   "smtp_password": "encrypted-or-placeholder",
--   "smtp_tls": true,
--   "from_address": "alerts@example.com",
--   "from_name": "OpsConductor Alerts"
-- }

ALTER TABLE integrations ADD COLUMN IF NOT EXISTS email_recipients JSONB;
-- email_recipients structure:
-- {
--   "to": ["admin@customer.com", "oncall@customer.com"],
--   "cc": [],
--   "bcc": []
-- }

ALTER TABLE integrations ADD COLUMN IF NOT EXISTS email_template JSONB;
-- email_template structure:
-- {
--   "subject_template": "[{severity}] Alert: {alert_type} on {device_id}",
--   "body_template": "html_or_text_template_string",
--   "format": "html"  -- or "text"
-- }

-- Add index for email integrations
CREATE INDEX IF NOT EXISTS idx_integrations_email
    ON integrations(tenant_id, type)
    WHERE type = 'email';

-- Update config constraint to include email requirements
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
    (type = 'webhook' AND (config_json->>'url') IS NOT NULL) OR
    (type = 'snmp' AND snmp_host IS NOT NULL AND snmp_config IS NOT NULL) OR
    (type = 'email' AND email_config IS NOT NULL AND email_recipients IS NOT NULL)
);

-- Comments for documentation
COMMENT ON COLUMN integrations.email_config IS 'SMTP server configuration for email integrations';
COMMENT ON COLUMN integrations.email_recipients IS 'Email recipient lists (to, cc, bcc)';
COMMENT ON COLUMN integrations.email_template IS 'Email subject and body templates';
