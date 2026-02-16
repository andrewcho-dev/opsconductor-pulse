BEGIN;

-- Dynamic device groups store a query_filter instead of explicit member rows.
CREATE TABLE IF NOT EXISTS dynamic_device_groups (
    tenant_id    TEXT        NOT NULL REFERENCES tenants(tenant_id) ON DELETE CASCADE,
    group_id     TEXT        NOT NULL,
    name         TEXT        NOT NULL,
    description  TEXT        NULL,
    query_filter JSONB       NOT NULL DEFAULT '{}',
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (tenant_id, group_id)
);

CREATE INDEX IF NOT EXISTS idx_dynamic_device_groups_tenant
    ON dynamic_device_groups(tenant_id);

-- RLS (matches existing device_groups pattern from migration 061)
ALTER TABLE dynamic_device_groups ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS dynamic_device_groups_tenant_isolation ON dynamic_device_groups;
CREATE POLICY dynamic_device_groups_tenant_isolation ON dynamic_device_groups
    USING (tenant_id = current_setting('app.tenant_id', true))
    WITH CHECK (tenant_id = current_setting('app.tenant_id', true));

COMMENT ON TABLE dynamic_device_groups IS
    'Device groups whose membership is resolved dynamically from query_filter JSONB.';
COMMENT ON COLUMN dynamic_device_groups.query_filter IS
    'Filter object. Supported keys: status (text), tags (text[]), site_id (text). Example: {"status":"ONLINE","tags":["production"],"site_id":"site-01"}';

COMMIT;

