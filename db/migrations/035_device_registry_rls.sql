-- Enable RLS on device_registry
ALTER TABLE device_registry ENABLE ROW LEVEL SECURITY;

-- Policy for tenant read/write
CREATE POLICY device_registry_tenant_policy ON device_registry
    FOR ALL
    USING (tenant_id = current_setting('app.tenant_id', true))
    WITH CHECK (tenant_id = current_setting('app.tenant_id', true));

-- Policy for operator read-only
CREATE POLICY device_registry_operator_read ON device_registry
    FOR SELECT
    TO pulse_operator
    USING (true);

-- Policy for iot service (ingest needs full access)
CREATE POLICY device_registry_service ON device_registry
    FOR ALL
    TO iot
    USING (true)
    WITH CHECK (true);

-- Enable RLS on delivery_jobs
ALTER TABLE delivery_jobs ENABLE ROW LEVEL SECURITY;

CREATE POLICY delivery_jobs_tenant_policy ON delivery_jobs
    FOR ALL
    USING (tenant_id = current_setting('app.tenant_id', true));

CREATE POLICY delivery_jobs_service ON delivery_jobs
    FOR ALL
    TO iot
    USING (true);

-- Enable RLS on quarantine_events
ALTER TABLE quarantine_events ENABLE ROW LEVEL SECURITY;

CREATE POLICY quarantine_events_tenant_policy ON quarantine_events
    FOR SELECT
    USING (tenant_id = current_setting('app.tenant_id', true));

CREATE POLICY quarantine_events_service ON quarantine_events
    FOR ALL
    TO iot
    USING (true);
