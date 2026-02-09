-- Migration: 027_metric_normalization.sql
-- Purpose: Metric normalization tables and RLS

CREATE TABLE IF NOT EXISTS normalized_metrics (
    id SERIAL PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    normalized_name TEXT NOT NULL,
    display_unit TEXT,
    description TEXT,
    expected_min NUMERIC,
    expected_max NUMERIC,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(tenant_id, normalized_name)
);

CREATE TABLE IF NOT EXISTS metric_mappings (
    id SERIAL PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    raw_metric TEXT NOT NULL,
    normalized_name TEXT NOT NULL,
    multiplier NUMERIC DEFAULT 1,
    offset_value NUMERIC DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(tenant_id, raw_metric),
    FOREIGN KEY (tenant_id, normalized_name)
        REFERENCES normalized_metrics(tenant_id, normalized_name) ON DELETE CASCADE
);

ALTER TABLE normalized_metrics ENABLE ROW LEVEL SECURITY;
ALTER TABLE metric_mappings ENABLE ROW LEVEL SECURITY;

CREATE POLICY normalized_metrics_tenant ON normalized_metrics
    FOR ALL USING (tenant_id = current_setting('app.tenant_id', true));

CREATE POLICY metric_mappings_tenant ON metric_mappings
    FOR ALL USING (tenant_id = current_setting('app.tenant_id', true));

GRANT SELECT, INSERT, UPDATE, DELETE ON normalized_metrics TO pulse_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON metric_mappings TO pulse_app;
GRANT USAGE, SELECT ON SEQUENCE normalized_metrics_id_seq TO pulse_app;
GRANT USAGE, SELECT ON SEQUENCE metric_mappings_id_seq TO pulse_app;
