# Phase 28.1: Create Tenants Table

## Task

Create an explicit tenants table to track tenant metadata.

## Create Migration

Create `db/migrations/018_tenants_table.sql`:

```sql
-- Tenants registry
CREATE TABLE IF NOT EXISTS tenants (
    tenant_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'ACTIVE',  -- ACTIVE, SUSPENDED, DELETED
    contact_email TEXT,
    contact_name TEXT,
    plan TEXT DEFAULT 'standard',  -- standard, premium, enterprise
    max_devices INT DEFAULT 100,
    max_rules INT DEFAULT 50,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at TIMESTAMPTZ  -- Soft delete
);

-- Index for listing active tenants
CREATE INDEX IF NOT EXISTS tenants_status_idx ON tenants(status) WHERE status != 'DELETED';

-- Enable RLS (operators only)
ALTER TABLE tenants ENABLE ROW LEVEL SECURITY;

-- Operators can read all tenants
CREATE POLICY tenant_operator_read ON tenants
    FOR SELECT TO pulse_operator USING (true);

-- Operators can manage tenants
CREATE POLICY tenant_operator_write ON tenants
    FOR ALL TO pulse_operator USING (true) WITH CHECK (true);

-- Customers can only see their own tenant (read-only)
CREATE POLICY tenant_customer_read ON tenants
    FOR SELECT TO pulse_app
    USING (tenant_id = current_setting('app.tenant_id', true));

-- Grant permissions
GRANT SELECT ON tenants TO pulse_app;
GRANT ALL ON tenants TO pulse_operator;

-- Seed existing tenants from device_registry (one-time migration)
INSERT INTO tenants (tenant_id, name, status, created_at)
SELECT DISTINCT
    tenant_id,
    tenant_id,  -- Use tenant_id as name initially
    'ACTIVE',
    MIN(provisioned_at)
FROM device_registry
WHERE tenant_id IS NOT NULL AND tenant_id != ''
GROUP BY tenant_id
ON CONFLICT (tenant_id) DO NOTHING;
```

## Apply Migration

The migration will be auto-applied when services start, or apply manually:

```bash
docker compose exec iot-postgres psql -U iot -d iotcloud -f /docker-entrypoint-initdb.d/018_tenants_table.sql
```

Or copy and execute:

```bash
docker compose exec iot-postgres psql -U iot -d iotcloud
```

Then paste the SQL.

## Verification

```bash
docker compose exec iot-postgres psql -U iot -d iotcloud -c "SELECT * FROM tenants"
```

Should show existing tenants seeded from device_registry.

## Files

| Action | File |
|--------|------|
| CREATE | `db/migrations/018_tenants_table.sql` |
