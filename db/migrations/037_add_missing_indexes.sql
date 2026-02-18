-- Single-column tenant_id index on device_registry for direct tenant lookups
CREATE INDEX IF NOT EXISTS idx_device_registry_tenant
ON device_registry(tenant_id);

-- Composite index for tenant + created_at on fleet_alert
CREATE INDEX IF NOT EXISTS idx_fleet_alert_tenant_created
ON fleet_alert(tenant_id, created_at DESC);

-- GIN index for telemetry metrics JSONB queries
CREATE INDEX IF NOT EXISTS idx_telemetry_metrics_gin
ON telemetry USING GIN (metrics);

-- Index for delivery_jobs tenant lookup
CREATE INDEX IF NOT EXISTS idx_delivery_jobs_tenant
ON delivery_jobs(tenant_id);

-- Index for subscription lookups by tenant
CREATE INDEX IF NOT EXISTS idx_subscriptions_tenant_type
ON subscriptions(tenant_id, subscription_type);
