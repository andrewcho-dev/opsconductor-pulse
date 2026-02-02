-- Test data for integration tests
-- Run with: psql -U iot -d iotcloud_test -f tests/fixtures/test_data.sql

-- Clear existing test data
DELETE FROM device_state WHERE tenant_id LIKE 'test-%';
DELETE FROM fleet_alert WHERE tenant_id LIKE 'test-%';
DELETE FROM integrations WHERE tenant_id LIKE 'test-%';

-- Tenant A data
INSERT INTO device_state (tenant_id, device_id, site_id, status, last_seen_at, state)
VALUES
    ('test-tenant-a', 'test-device-a1', 'test-site-a', 'ONLINE', now(), '{"battery_pct": 85, "temp_c": 22.5}'),
    ('test-tenant-a', 'test-device-a2', 'test-site-a', 'STALE', now() - interval '2 hours', '{"battery_pct": 20, "temp_c": 25.0}');

-- Tenant B data
INSERT INTO device_state (tenant_id, device_id, site_id, status, last_seen_at, state)
VALUES
    ('test-tenant-b', 'test-device-b1', 'test-site-b', 'ONLINE', now(), '{"battery_pct": 90, "temp_c": 21.0}');

-- Test alerts
INSERT INTO fleet_alert (tenant_id, device_id, site_id, alert_type, severity, summary, status, created_at)
VALUES
    ('test-tenant-a', 'test-device-a2', 'test-site-a', 'LOW_BATTERY', 'WARNING', 'Battery below 25%', 'OPEN', now());
