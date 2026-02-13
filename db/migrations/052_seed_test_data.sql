-- ============================================
-- Migration: 052_seed_test_data.sql
-- Purpose: Seed fresh test data (Acme Industrial, 12 devices)
-- ============================================

BEGIN;

-- ============================================
-- 0. Optional schema for seed (if not exists)
-- ============================================

ALTER TABLE device_registry
    ADD COLUMN IF NOT EXISTS device_type TEXT;

CREATE TABLE IF NOT EXISTS sites (
    site_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL REFERENCES tenants(tenant_id),
    name TEXT NOT NULL,
    location TEXT,
    latitude DOUBLE PRECISION,
    longitude DOUBLE PRECISION,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS device_extended_attributes (
    device_id TEXT NOT NULL,
    tenant_id TEXT NOT NULL,
    attributes JSONB NOT NULL DEFAULT '{}',
    PRIMARY KEY (tenant_id, device_id),
    FOREIGN KEY (tenant_id, device_id)
        REFERENCES device_registry (tenant_id, device_id) ON DELETE CASCADE
);

ALTER TABLE alert_rules ADD COLUMN IF NOT EXISTS device_type TEXT;
ALTER TABLE alert_rules ADD COLUMN IF NOT EXISTS metric_name TEXT;

-- ============================================
-- 1. Tenant
-- ============================================

INSERT INTO tenants (tenant_id, name, status, created_at)
VALUES (
    'acme-industrial',
    'Acme Industrial',
    'ACTIVE',
    now()
)
ON CONFLICT (tenant_id) DO UPDATE
SET name = EXCLUDED.name, status = EXCLUDED.status;

-- ============================================
-- 2. Site
-- ============================================

INSERT INTO sites (site_id, tenant_id, name, location, latitude, longitude, created_at)
VALUES (
    'acme-hq',
    'acme-industrial',
    'HQ',
    'Chicago, IL',
    41.8781,
    -87.6298,
    now()
)
ON CONFLICT (site_id) DO UPDATE
SET name = EXCLUDED.name, location = EXCLUDED.location;

-- ============================================
-- 3. Subscription
-- ============================================

INSERT INTO subscriptions (
    subscription_id,
    tenant_id,
    subscription_type,
    device_limit,
    active_device_count,
    term_start,
    term_end,
    status,
    created_at
)
VALUES (
    'sub-acme-main-001',
    'acme-industrial',
    'MAIN',
    25,
    0,
    now(),
    now() + interval '1 year',
    'ACTIVE',
    now()
)
ON CONFLICT (subscription_id) DO UPDATE
SET device_limit = EXCLUDED.device_limit,
    term_end = EXCLUDED.term_end,
    status = EXCLUDED.status;

-- ============================================
-- 4. Devices (12)
-- ============================================

INSERT INTO device_registry (
    device_id, tenant_id, site_id, subscription_id, device_type, model, status, created_at
)
VALUES
    ('SENSOR-001', 'acme-industrial', 'acme-hq', 'sub-acme-main-001', 'temperature', 'Tempix T200', 'ACTIVE', now() - interval '18 months'),
    ('SENSOR-002', 'acme-industrial', 'acme-hq', 'sub-acme-main-001', 'temperature', 'Tempix T200', 'ACTIVE', now() - interval '15 months'),
    ('SENSOR-003', 'acme-industrial', 'acme-hq', 'sub-acme-main-001', 'humidity', 'HumidPro H50', 'ACTIVE', now() - interval '18 months'),
    ('SENSOR-004', 'acme-industrial', 'acme-hq', 'sub-acme-main-001', 'pressure', 'BaroSense P100', 'ACTIVE', now() - interval '12 months'),
    ('SENSOR-005', 'acme-industrial', 'acme-hq', 'sub-acme-main-001', 'temperature', 'Tempix T200', 'ACTIVE', now() - interval '12 months'),
    ('SENSOR-006', 'acme-industrial', 'acme-hq', 'sub-acme-main-001', 'power', 'PowerMeter PM3000', 'ACTIVE', now() - interval '24 months'),
    ('SENSOR-007', 'acme-industrial', 'acme-hq', 'sub-acme-main-001', 'vibration', 'VibeTech V400', 'ACTIVE', now() - interval '8 months'),
    ('SENSOR-008', 'acme-industrial', 'acme-hq', 'sub-acme-main-001', 'temperature', 'Tempix T100', 'INACTIVE', now() - interval '20 months'),
    ('SENSOR-009', 'acme-industrial', 'acme-hq', 'sub-acme-main-001', 'flow', 'FlowMax F200', 'ACTIVE', now() - interval '14 months'),
    ('SENSOR-010', 'acme-industrial', 'acme-hq', 'sub-acme-main-001', 'level', 'TankLevel TL50', 'ACTIVE', now() - interval '10 months'),
    ('SENSOR-011', 'acme-industrial', 'acme-hq', 'sub-acme-main-001', 'temperature', 'Tempix T200', 'SUSPENDED', now() - interval '7 days'),
    ('SENSOR-012', 'acme-industrial', 'acme-hq', 'sub-acme-main-001', 'gateway', 'EdgeGate EG100', 'ACTIVE', now() - interval '20 months')
ON CONFLICT (tenant_id, device_id) DO UPDATE
SET site_id = EXCLUDED.site_id,
    subscription_id = EXCLUDED.subscription_id,
    device_type = EXCLUDED.device_type,
    model = EXCLUDED.model,
    status = EXCLUDED.status;

-- Extended attributes (only if table exists and supports upsert)
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'device_extended_attributes') THEN
        INSERT INTO device_extended_attributes (device_id, tenant_id, attributes)
        VALUES
            ('SENSOR-001', 'acme-industrial', '{"manufacturer":"Tempix","model":"T200","firmware_version":"2.4.1","location":"Building A - Server Room"}'::jsonb),
            ('SENSOR-002', 'acme-industrial', '{"manufacturer":"Tempix","model":"T200","location":"Building A - Warehouse"}'::jsonb),
            ('SENSOR-003', 'acme-industrial', '{"manufacturer":"HumidPro","model":"H50","location":"Building A - Server Room"}'::jsonb),
            ('SENSOR-004', 'acme-industrial', '{"manufacturer":"BaroSense","model":"P100","location":"Building B - Lab"}'::jsonb),
            ('SENSOR-005', 'acme-industrial', '{"manufacturer":"Tempix","model":"T200","location":"Building B - Lab"}'::jsonb),
            ('SENSOR-006', 'acme-industrial', '{"manufacturer":"PowerMeter","model":"PM3000","location":"Building A - Electrical Room"}'::jsonb),
            ('SENSOR-007', 'acme-industrial', '{"manufacturer":"VibeTech","model":"V400","location":"Building B - Machinery Hall"}'::jsonb),
            ('SENSOR-008', 'acme-industrial', '{"manufacturer":"Tempix","model":"T100","location":"Building C - Storage"}'::jsonb),
            ('SENSOR-009', 'acme-industrial', '{"manufacturer":"FlowMax","model":"F200","location":"Building A - HVAC Room"}'::jsonb),
            ('SENSOR-010', 'acme-industrial', '{"manufacturer":"TankLevel","model":"TL50","location":"Building B - Tank Farm"}'::jsonb),
            ('SENSOR-011', 'acme-industrial', '{"manufacturer":"Tempix","model":"T200","location":"Building C - New Wing"}'::jsonb),
            ('SENSOR-012', 'acme-industrial', '{"manufacturer":"EdgeGate","model":"EG100","location":"Building A - Network Closet"}'::jsonb)
        ON CONFLICT (tenant_id, device_id) DO UPDATE SET attributes = EXCLUDED.attributes;
    END IF;
END $$;

-- ============================================
-- 5. Update subscription device count
-- ============================================

UPDATE subscriptions
SET active_device_count = (
    SELECT COUNT(*) FROM device_registry
    WHERE tenant_id = 'acme-industrial' AND status = 'ACTIVE'
)
WHERE subscription_id = 'sub-acme-main-001';

-- ============================================
-- 6. Alert rules (metric_name, severity text)
-- ============================================

DO $$
DECLARE
    severity_type TEXT;
BEGIN
    SELECT data_type INTO severity_type
    FROM information_schema.columns
    WHERE table_schema = 'public'
      AND table_name = 'alert_rules'
      AND column_name = 'severity';

    IF NOT EXISTS (SELECT 1 FROM alert_rules WHERE tenant_id = 'acme-industrial') THEN
        IF severity_type = 'integer' THEN
            INSERT INTO alert_rules (
                tenant_id, name, device_type, metric_name, operator, threshold, severity, enabled
            )
            VALUES
                ('acme-industrial', 'High Temperature Alert', 'temperature', 'temperature', '>', 30::numeric, 4, true),
                ('acme-industrial', 'Critical Temperature', 'temperature', 'temperature', '>', 40::numeric, 5, true),
                ('acme-industrial', 'Low Humidity Alert', 'humidity', 'humidity', '<', 30::numeric, 4, true),
                ('acme-industrial', 'High Vibration', 'vibration', 'vibration_rms', '>', 5.0, 4, true),
                ('acme-industrial', 'Tank Low Level', 'level', 'level_percent', '<', 20::numeric, 4, true),
                ('acme-industrial', 'Power Anomaly', 'power', 'power_factor', '<', 0.85, 4, true);
        ELSE
            INSERT INTO alert_rules (
                tenant_id, name, device_type, metric_name, operator, threshold, severity, enabled
            )
            VALUES
                ('acme-industrial', 'High Temperature Alert', 'temperature', 'temperature', '>', 30::numeric, 'high', true),
                ('acme-industrial', 'Critical Temperature', 'temperature', 'temperature', '>', 40::numeric, 'critical', true),
                ('acme-industrial', 'Low Humidity Alert', 'humidity', 'humidity', '<', 30::numeric, 'high', true),
                ('acme-industrial', 'High Vibration', 'vibration', 'vibration_rms', '>', 5.0, 'high', true),
                ('acme-industrial', 'Tank Low Level', 'level', 'level_percent', '<', 20::numeric, 'high', true),
                ('acme-industrial', 'Power Anomaly', 'power', 'power_factor', '<', 0.85, 'high', true);
        END IF;
    END IF;
END $$;

-- ============================================
-- 7. Verification
-- ============================================

DO $$
DECLARE
    tenant_count INT;
    site_count INT;
    device_count INT;
    active_count INT;
BEGIN
    SELECT COUNT(*) INTO tenant_count FROM tenants WHERE tenant_id = 'acme-industrial';
    SELECT COUNT(*) INTO site_count FROM sites WHERE tenant_id = 'acme-industrial';
    SELECT COUNT(*) INTO device_count FROM device_registry WHERE tenant_id = 'acme-industrial';
    SELECT COUNT(*) INTO active_count FROM device_registry WHERE tenant_id = 'acme-industrial' AND status = 'ACTIVE';
    RAISE NOTICE 'Seed complete: Tenants=%, Sites=%, Devices=% (% active)',
        tenant_count, site_count, device_count, active_count;
END $$;

COMMIT;
