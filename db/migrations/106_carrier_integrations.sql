-- Migration 106: Carrier integration credentials and configuration
-- Stores per-tenant MVNO/carrier API credentials for diagnostics, usage sync, and remote commands.

CREATE TABLE IF NOT EXISTS carrier_integrations (
    id              SERIAL PRIMARY KEY,
    tenant_id       TEXT NOT NULL REFERENCES tenants(tenant_id) ON DELETE CASCADE,
    carrier_name    TEXT NOT NULL,                   -- 'hologram', '1nce', 'jasper', 'twilio_iot', 'custom'
    display_name    TEXT NOT NULL,                   -- User-friendly name (e.g., "Hologram Production")
    enabled         BOOLEAN NOT NULL DEFAULT true,

    -- API credentials (encrypted at rest via app-level encryption)
    api_key         TEXT,                            -- Primary API key or token
    api_secret      TEXT,                            -- Secondary secret (if needed)
    api_base_url    TEXT,                            -- Custom base URL (for self-hosted or sandbox)
    account_id      TEXT,                            -- Carrier account/org identifier

    -- Configuration
    config          JSONB NOT NULL DEFAULT '{}',     -- Carrier-specific config (e.g., org_id, pool_id, webhook_url)

    -- Sync settings
    sync_enabled    BOOLEAN NOT NULL DEFAULT true,
    sync_interval_minutes INT NOT NULL DEFAULT 60,   -- How often to pull usage data
    last_sync_at    TIMESTAMPTZ,
    last_sync_status TEXT DEFAULT 'never',            -- 'success', 'error', 'never'
    last_sync_error TEXT,

    -- Metadata
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),

    -- One integration per carrier per tenant
    UNIQUE (tenant_id, carrier_name)
);

-- Indexes
CREATE INDEX idx_carrier_integrations_tenant ON carrier_integrations(tenant_id);
CREATE INDEX idx_carrier_integrations_sync ON carrier_integrations(sync_enabled, last_sync_at)
    WHERE sync_enabled = true AND enabled = true;

-- RLS
ALTER TABLE carrier_integrations ENABLE ROW LEVEL SECURITY;

CREATE POLICY carrier_integrations_tenant ON carrier_integrations
    USING (tenant_id = current_setting('app.tenant_id', true))
    WITH CHECK (tenant_id = current_setting('app.tenant_id', true));

CREATE POLICY carrier_integrations_operator_read ON carrier_integrations
    FOR SELECT
    USING (current_setting('app.role', true) = 'operator');

-- Updated_at trigger
CREATE TRIGGER trg_carrier_integrations_updated_at
    BEFORE UPDATE ON carrier_integrations
    FOR EACH ROW
    EXECUTE FUNCTION update_sensors_timestamp();

-- Also add a carrier_device_id column to device_connections
-- This maps our device to the carrier's device/SIM identifier
ALTER TABLE device_connections ADD COLUMN IF NOT EXISTS carrier_device_id TEXT;
ALTER TABLE device_connections ADD COLUMN IF NOT EXISTS carrier_integration_id INT
    REFERENCES carrier_integrations(id) ON DELETE SET NULL;

COMMENT ON COLUMN device_connections.carrier_device_id IS
    'The carrier-side identifier for this device/SIM (e.g., Hologram device ID, Jasper ICCID)';
COMMENT ON COLUMN device_connections.carrier_integration_id IS
    'Links this connection to a specific carrier integration for API calls';

