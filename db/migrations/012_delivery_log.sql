CREATE TABLE IF NOT EXISTS delivery_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    alert_id VARCHAR(64) NOT NULL,
    integration_id UUID NOT NULL,
    integration_name VARCHAR(128),
    delivery_type VARCHAR(16) NOT NULL,
    tenant_id VARCHAR(64) NOT NULL,
    success BOOLEAN NOT NULL,
    error TEXT,
    duration_ms FLOAT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_delivery_log_alert_id ON delivery_log(alert_id);
CREATE INDEX IF NOT EXISTS idx_delivery_log_tenant_id ON delivery_log(tenant_id);
CREATE INDEX IF NOT EXISTS idx_delivery_log_created_at ON delivery_log(created_at);

ALTER TABLE delivery_log ENABLE ROW LEVEL SECURITY;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies
        WHERE policyname = 'delivery_log_tenant_policy'
          AND tablename = 'delivery_log'
    ) THEN
        CREATE POLICY delivery_log_tenant_policy ON delivery_log
            FOR ALL USING (tenant_id = current_setting('app.tenant_id', true));
    END IF;
END$$;

GRANT SELECT, INSERT ON delivery_log TO pulse_app;
GRANT SELECT ON delivery_log TO pulse_operator;
