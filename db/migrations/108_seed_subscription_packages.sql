-- Migration 108: Seed subscription package data
-- Date: 2026-02-18

BEGIN;

-- ═══════════════════════════════════════════════════════════════════
-- Account Tiers (per-tenant shared resources)
-- ═══════════════════════════════════════════════════════════════════

INSERT INTO account_tiers (tier_id, name, description, limits, features, support, monthly_price_cents, annual_price_cents, sort_order) VALUES

('free', 'Free', 'Get started with basic IoT monitoring', '{
    "users": 2,
    "alert_rules": 5,
    "notification_channels": 2,
    "dashboards_per_user": 3,
    "device_groups": 3,
    "api_requests_per_minute": 30
}'::jsonb, '{
    "sso": false,
    "custom_branding": false,
    "audit_log_export": false,
    "bulk_device_import": false,
    "carrier_self_service": false,
    "alert_escalation": false,
    "oncall_scheduling": false,
    "maintenance_windows": false
}'::jsonb, '{
    "level": "community",
    "sla_uptime_pct": null,
    "response_time_hours": null,
    "dedicated_csm": false
}'::jsonb, 0, 0, 1),

('growth', 'Growth', 'Scale your IoT fleet with full platform capabilities', '{
    "users": 10,
    "alert_rules": 100,
    "notification_channels": 10,
    "dashboards_per_user": 10,
    "device_groups": 25,
    "api_requests_per_minute": 300
}'::jsonb, '{
    "sso": false,
    "custom_branding": false,
    "audit_log_export": true,
    "bulk_device_import": true,
    "carrier_self_service": true,
    "alert_escalation": true,
    "oncall_scheduling": true,
    "maintenance_windows": true
}'::jsonb, '{
    "level": "standard",
    "sla_uptime_pct": 99.5,
    "response_time_hours": 8,
    "dedicated_csm": false
}'::jsonb, 4900, 49000, 2),

('scale', 'Scale', 'Enterprise-grade IoT management at scale', '{
    "users": 50,
    "alert_rules": 1000,
    "notification_channels": 50,
    "dashboards_per_user": 25,
    "device_groups": 100,
    "api_requests_per_minute": 1500
}'::jsonb, '{
    "sso": true,
    "custom_branding": false,
    "audit_log_export": true,
    "bulk_device_import": true,
    "carrier_self_service": true,
    "alert_escalation": true,
    "oncall_scheduling": true,
    "maintenance_windows": true
}'::jsonb, '{
    "level": "business",
    "sla_uptime_pct": 99.9,
    "response_time_hours": 4,
    "dedicated_csm": false
}'::jsonb, 14900, 149000, 3),

('enterprise', 'Enterprise', 'Custom solutions with dedicated support and white-glove onboarding', '{
    "users": 500,
    "alert_rules": 10000,
    "notification_channels": 100,
    "dashboards_per_user": 50,
    "device_groups": 500,
    "api_requests_per_minute": 6000
}'::jsonb, '{
    "sso": true,
    "custom_branding": true,
    "audit_log_export": true,
    "bulk_device_import": true,
    "carrier_self_service": true,
    "alert_escalation": true,
    "oncall_scheduling": true,
    "maintenance_windows": true
}'::jsonb, '{
    "level": "enterprise",
    "sla_uptime_pct": 99.99,
    "response_time_hours": 1,
    "dedicated_csm": true
}'::jsonb, 49900, 499000, 4)

ON CONFLICT (tier_id) DO NOTHING;

-- ═══════════════════════════════════════════════════════════════════
-- Device Plans (per-device capabilities + pricing)
-- ═══════════════════════════════════════════════════════════════════

INSERT INTO device_plans (plan_id, name, description, limits, features, monthly_price_cents, annual_price_cents, sort_order) VALUES

('basic', 'Basic', 'Essential telemetry and alerting for simple sensors', '{
    "sensors": 5,
    "data_retention_days": 30,
    "telemetry_rate_per_minute": 12,
    "health_telemetry_interval_seconds": 300
}'::jsonb, '{
    "ota_updates": false,
    "advanced_analytics": false,
    "streaming_export": false,
    "x509_auth": false,
    "message_routing": false,
    "device_commands": true,
    "device_twin": false,
    "carrier_diagnostics": true
}'::jsonb, 299, 2990, 1),

('standard', 'Standard', 'Full-featured device management with OTA and analytics', '{
    "sensors": 15,
    "data_retention_days": 90,
    "telemetry_rate_per_minute": 60,
    "health_telemetry_interval_seconds": 120
}'::jsonb, '{
    "ota_updates": true,
    "advanced_analytics": true,
    "streaming_export": true,
    "x509_auth": false,
    "message_routing": false,
    "device_commands": true,
    "device_twin": true,
    "carrier_diagnostics": true
}'::jsonb, 999, 9990, 2),

('premium', 'Premium', 'Mission-critical devices with maximum security and throughput', '{
    "sensors": 30,
    "data_retention_days": 365,
    "telemetry_rate_per_minute": 120,
    "health_telemetry_interval_seconds": 60
}'::jsonb, '{
    "ota_updates": true,
    "advanced_analytics": true,
    "streaming_export": true,
    "x509_auth": true,
    "message_routing": true,
    "device_commands": true,
    "device_twin": true,
    "carrier_diagnostics": true
}'::jsonb, 2499, 24990, 3)

ON CONFLICT (plan_id) DO NOTHING;

-- ═══════════════════════════════════════════════════════════════════
-- Assign account tier to seed tenant
-- ═══════════════════════════════════════════════════════════════════

UPDATE tenants SET account_tier_id = 'growth' WHERE tenant_id = 'acme-industrial';

-- ═══════════════════════════════════════════════════════════════════
-- Assign device plans to seed devices
-- ═══════════════════════════════════════════════════════════════════

-- GW-001 and GW-002: Standard plan (Hologram-linked, active)
UPDATE device_registry SET plan_id = 'standard' WHERE device_id IN ('GW-001', 'GW-002') AND tenant_id = 'acme-industrial';

-- GW-003: Basic plan
UPDATE device_registry SET plan_id = 'basic' WHERE device_id = 'GW-003' AND tenant_id = 'acme-industrial';

-- GW-004: Premium plan (1NCE-linked, critical gateway)
UPDATE device_registry SET plan_id = 'premium' WHERE device_id = 'GW-004' AND tenant_id = 'acme-industrial';

-- ═══════════════════════════════════════════════════════════════════
-- Create device subscriptions for seed devices
-- ═══════════════════════════════════════════════════════════════════

INSERT INTO device_subscriptions (subscription_id, tenant_id, device_id, plan_id, status, term_start, term_end) VALUES
    ('DSUB-20260101-GW001', 'acme-industrial', 'GW-001', 'standard', 'ACTIVE', '2026-01-01', '2027-01-01'),
    ('DSUB-20260101-GW002', 'acme-industrial', 'GW-002', 'standard', 'ACTIVE', '2026-01-01', '2027-01-01'),
    ('DSUB-20260115-GW003', 'acme-industrial', 'GW-003', 'basic',    'ACTIVE', '2026-01-15', '2027-01-15'),
    ('DSUB-20260201-GW004', 'acme-industrial', 'GW-004', 'premium',  'ACTIVE', '2026-02-01', '2027-02-01')
ON CONFLICT DO NOTHING;

COMMIT;
