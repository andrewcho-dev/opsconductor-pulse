-- System-wide audit log - captures ALL events
CREATE TABLE IF NOT EXISTS audit_log (
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Tenant (NULL for system-level events)
    tenant_id TEXT,

    -- Event classification
    event_type TEXT NOT NULL,
    category TEXT NOT NULL,
    severity TEXT NOT NULL DEFAULT 'info',

    -- What was affected
    entity_type TEXT,
    entity_id TEXT,
    entity_name TEXT,

    -- What happened
    action TEXT NOT NULL,
    message TEXT NOT NULL,
    details JSONB,

    -- Source
    source_service TEXT NOT NULL,
    actor_type TEXT DEFAULT 'system',
    actor_id TEXT,
    actor_name TEXT,

    -- Request context
    ip_address INET,
    request_id TEXT,
    duration_ms INTEGER
);

-- Convert to TimescaleDB hypertable (auto-partitioned by time)
SELECT create_hypertable(
    'audit_log',
    'timestamp',
    chunk_time_interval => INTERVAL '1 day',
    if_not_exists => TRUE
);

-- Indexes for common queries
CREATE INDEX idx_audit_tenant_time ON audit_log(tenant_id, timestamp DESC) WHERE tenant_id IS NOT NULL;
CREATE INDEX idx_audit_category_time ON audit_log(category, timestamp DESC);
CREATE INDEX idx_audit_severity_time ON audit_log(severity, timestamp DESC) WHERE severity IN ('warning', 'error', 'critical');
CREATE INDEX idx_audit_entity ON audit_log(entity_type, entity_id, timestamp DESC);
CREATE INDEX idx_audit_source ON audit_log(source_service, timestamp DESC);

-- Note: Audit log compression is intentionally omitted because columnstore
-- compression is incompatible with the RLS configuration used on this table.

-- Retention policy - drop chunks older than 90 days
SELECT add_retention_policy('audit_log', INTERVAL '90 days', if_not_exists => TRUE);

-- RLS for tenant isolation
ALTER TABLE audit_log ENABLE ROW LEVEL SECURITY;

CREATE POLICY audit_log_tenant_read ON audit_log
    FOR SELECT USING (
        tenant_id IS NULL
        OR tenant_id = current_setting('app.tenant_id', true)
    );

-- Grants
GRANT SELECT ON audit_log TO pulse_app;
GRANT SELECT ON audit_log TO pulse_operator;
GRANT INSERT ON audit_log TO pulse_app;
