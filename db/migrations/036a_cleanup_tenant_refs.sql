-- Clean up invalid tenant_id references before adding FKs

-- Option 1: Delete orphaned rows (if test data)
DELETE FROM device_state WHERE tenant_id = 'enabled';
DELETE FROM fleet_alert WHERE tenant_id = 'enabled';

-- Option 2: If real data, assign to a valid tenant
-- First check what tenants exist:
-- SELECT tenant_id FROM tenants LIMIT 5;
-- Then update:
-- UPDATE device_state SET tenant_id = 'actual-tenant-id' WHERE tenant_id = 'enabled';
-- UPDATE fleet_alert SET tenant_id = 'actual-tenant-id' WHERE tenant_id = 'enabled';

-- Also check for any other invalid references
DELETE FROM device_state WHERE tenant_id NOT IN (SELECT tenant_id FROM tenants);
DELETE FROM fleet_alert WHERE tenant_id NOT IN (SELECT tenant_id FROM tenants);
DELETE FROM device_registry WHERE tenant_id NOT IN (SELECT tenant_id FROM tenants);
DELETE FROM alert_rules WHERE tenant_id NOT IN (SELECT tenant_id FROM tenants);
DELETE FROM integration_routes WHERE tenant_id NOT IN (SELECT tenant_id FROM tenants);
DELETE FROM integrations WHERE tenant_id NOT IN (SELECT tenant_id FROM tenants);
