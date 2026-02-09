-- Migration: 026_metric_catalog.sql
-- Purpose: Metric enrichment catalog per tenant

CREATE TABLE IF NOT EXISTS metric_catalog (
    id SERIAL PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    metric_name TEXT NOT NULL,
    description TEXT,
    unit TEXT,
    expected_min NUMERIC,
    expected_max NUMERIC,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(tenant_id, metric_name)
);

ALTER TABLE metric_catalog ENABLE ROW LEVEL SECURITY;

CREATE POLICY metric_catalog_tenant_isolation ON metric_catalog
    FOR ALL USING (tenant_id = current_setting('app.tenant_id', true));

GRANT SELECT, INSERT, UPDATE, DELETE ON metric_catalog TO pulse_app;
GRANT USAGE, SELECT ON SEQUENCE metric_catalog_id_seq TO pulse_app;
