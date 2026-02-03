-- Add integration type enum if not exists
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'integration_type') THEN
        CREATE TYPE integration_type AS ENUM ('webhook', 'snmp');
    END IF;
END$$;

-- Add type column to integrations (default webhook for existing rows)
ALTER TABLE integrations
ADD COLUMN IF NOT EXISTS type integration_type NOT NULL DEFAULT 'webhook';

DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'integrations_type_check'
    ) THEN
        ALTER TABLE integrations DROP CONSTRAINT integrations_type_check;
    END IF;
END$$;

DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_name = 'integrations'
          AND column_name = 'type'
          AND data_type = 'text'
    ) THEN
        ALTER TABLE integrations ALTER COLUMN type DROP DEFAULT;
        ALTER TABLE integrations
        ALTER COLUMN type TYPE integration_type
        USING type::integration_type;
    END IF;
END$$;

ALTER TABLE integrations
ALTER COLUMN type SET DEFAULT 'webhook';

-- Add SNMP configuration column (JSON)
-- Structure for SNMPv2c: {"version": "2c", "community": "public"}
-- Structure for SNMPv3: {"version": "3", "username": "...", "auth_protocol": "SHA", "auth_password": "...", "priv_protocol": "AES", "priv_password": "..."}
ALTER TABLE integrations
ADD COLUMN IF NOT EXISTS snmp_config JSONB;

-- Add SNMP destination columns
ALTER TABLE integrations
ADD COLUMN IF NOT EXISTS snmp_host VARCHAR(255);

ALTER TABLE integrations
ADD COLUMN IF NOT EXISTS snmp_port INTEGER DEFAULT 162;

-- Add constraint: webhook requires webhook URL config, snmp requires snmp_host
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'integration_type_config_check'
    ) THEN
        ALTER TABLE integrations
        ADD CONSTRAINT integration_type_config_check CHECK (
            (type = 'webhook' AND (config_json->>'url') IS NOT NULL) OR
            (type = 'snmp' AND snmp_host IS NOT NULL AND snmp_config IS NOT NULL)
        );
    END IF;
END$$;

-- Index for type queries
CREATE INDEX IF NOT EXISTS idx_integrations_type ON integrations(type);

-- Add SNMP-specific OID configuration
-- Default OIDs for alert traps
ALTER TABLE integrations
ADD COLUMN IF NOT EXISTS snmp_oid_prefix VARCHAR(128) DEFAULT '1.3.6.1.4.1.99999';

COMMENT ON COLUMN integrations.type IS 'Integration output type: webhook or snmp';
COMMENT ON COLUMN integrations.snmp_config IS 'SNMP authentication config (v2c community or v3 credentials)';
COMMENT ON COLUMN integrations.snmp_host IS 'SNMP trap destination hostname or IP';
COMMENT ON COLUMN integrations.snmp_port IS 'SNMP trap destination port (default 162)';
COMMENT ON COLUMN integrations.snmp_oid_prefix IS 'Base OID for trap varbinds';
