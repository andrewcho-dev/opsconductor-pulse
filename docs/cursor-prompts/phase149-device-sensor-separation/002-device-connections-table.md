# Task 002 — Create `device_connections` Table

## Migration File

Create `db/migrations/100_device_connections.sql`

## SQL

```sql
-- Migration 100: Create device_connections table
-- Tracks the cellular/network connection associated with each device/gateway.
-- One connection per device (1:1 relationship).
-- Stores carrier details, SIM status, data plan info, and connection diagnostics.

CREATE TABLE IF NOT EXISTS device_connections (
    id              SERIAL PRIMARY KEY,
    tenant_id       TEXT NOT NULL,
    device_id       TEXT NOT NULL,

    -- Connection type
    connection_type TEXT NOT NULL DEFAULT 'cellular'
                    CHECK (connection_type IN ('cellular', 'ethernet', 'wifi', 'lora', 'satellite', 'other')),

    -- Cellular/carrier details
    carrier_name    TEXT,                   -- MVNO/carrier name (e.g., "Hologram", "1NCE", "AT&T")
    carrier_account_id TEXT,               -- Account ID with the carrier
    plan_name       TEXT,                   -- Plan/rate plan name
    apn             TEXT,                   -- Access Point Name for cellular

    -- SIM identity
    sim_iccid       TEXT,                   -- SIM card ICCID (may duplicate device_registry.iccid initially)
    sim_status      TEXT DEFAULT 'active'
                    CHECK (sim_status IN ('active', 'suspended', 'deactivated', 'ready', 'unknown')),

    -- Data plan
    data_limit_mb   INT,                    -- Monthly data cap in MB (NULL = unlimited)
    billing_cycle_start INT DEFAULT 1,     -- Day of month billing resets (1-28)
    data_used_mb    NUMERIC DEFAULT 0,      -- Current cycle usage (synced from carrier API)
    data_used_updated_at TIMESTAMPTZ,       -- When data_used_mb was last synced

    -- Network assignment
    ip_address      INET,                   -- Current IP address
    msisdn          TEXT,                   -- Phone number (if applicable)

    -- Status tracking
    network_status  TEXT DEFAULT 'unknown'
                    CHECK (network_status IN ('connected', 'disconnected', 'suspended', 'unknown')),
    last_network_attach TIMESTAMPTZ,        -- Last time device attached to network
    last_network_detach TIMESTAMPTZ,        -- Last time device detached

    -- Metadata
    metadata        JSONB NOT NULL DEFAULT '{}',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),

    -- One connection per device
    UNIQUE (tenant_id, device_id),

    -- FK to device_registry
    FOREIGN KEY (tenant_id, device_id)
        REFERENCES device_registry(tenant_id, device_id)
        ON DELETE CASCADE
);

-- Indexes
CREATE INDEX idx_device_connections_tenant ON device_connections(tenant_id);
CREATE INDEX idx_device_connections_carrier ON device_connections(tenant_id, carrier_name)
    WHERE carrier_name IS NOT NULL;
CREATE INDEX idx_device_connections_status ON device_connections(tenant_id, network_status);
CREATE INDEX idx_device_connections_sim ON device_connections(sim_iccid)
    WHERE sim_iccid IS NOT NULL;

-- RLS
ALTER TABLE device_connections ENABLE ROW LEVEL SECURITY;

CREATE POLICY device_connections_tenant_isolation ON device_connections
    USING (tenant_id = current_setting('app.tenant_id', true))
    WITH CHECK (tenant_id = current_setting('app.tenant_id', true));

CREATE POLICY device_connections_operator_read ON device_connections
    FOR SELECT
    USING (current_setting('app.role', true) = 'operator');

CREATE POLICY device_connections_service ON device_connections
    USING (current_setting('app.role', true) = 'iot_service')
    WITH CHECK (current_setting('app.role', true) = 'iot_service');

-- Updated_at trigger
CREATE TRIGGER trg_device_connections_updated_at
    BEFORE UPDATE ON device_connections
    FOR EACH ROW
    EXECUTE FUNCTION update_sensors_timestamp();
    -- Reuses the generic timestamp trigger from migration 099
```

## Notes

- 1:1 relationship with device_registry via UNIQUE(tenant_id, device_id)
- `sim_iccid` may initially duplicate `device_registry.iccid` — in Phase 153 (carrier integration), this becomes the authoritative SIM reference
- `data_used_mb` is a cached value synced periodically from the carrier API (Phase 153)
- `billing_cycle_start` allows tracking when the data cap resets each month
- `connection_type` supports future non-cellular devices but defaults to cellular
- The `metadata` JSONB field allows carrier-specific data without schema changes

## Verification

```bash
psql -d iot -f db/migrations/100_device_connections.sql
psql -d iot -c "\d device_connections"
```
