-- Add FK from device_registry to tenants
ALTER TABLE device_registry
ADD CONSTRAINT fk_device_registry_tenant
FOREIGN KEY (tenant_id) REFERENCES tenants(tenant_id)
ON DELETE CASCADE;

-- Add FK from device_state to tenants
ALTER TABLE device_state
ADD CONSTRAINT fk_device_state_tenant
FOREIGN KEY (tenant_id) REFERENCES tenants(tenant_id)
ON DELETE CASCADE;

-- Add FK from alert_rules to tenants
ALTER TABLE alert_rules
ADD CONSTRAINT fk_alert_rules_tenant
FOREIGN KEY (tenant_id) REFERENCES tenants(tenant_id)
ON DELETE CASCADE;

-- Add FK from fleet_alert to tenants
ALTER TABLE fleet_alert
ADD CONSTRAINT fk_fleet_alert_tenant
FOREIGN KEY (tenant_id) REFERENCES tenants(tenant_id)
ON DELETE CASCADE;

-- Add FK from integration_routes to tenants
ALTER TABLE integration_routes
ADD CONSTRAINT fk_integration_routes_tenant
FOREIGN KEY (tenant_id) REFERENCES tenants(tenant_id)
ON DELETE CASCADE;

-- Add FK from integrations to tenants
ALTER TABLE integrations
ADD CONSTRAINT fk_integrations_tenant
FOREIGN KEY (tenant_id) REFERENCES tenants(tenant_id)
ON DELETE CASCADE;
