-- Migration 107: Subscription Package Architecture
-- Date: 2026-02-18
-- Clean break: drops all old plan/tier/subscription tables, creates new model.

BEGIN;

-- ═══════════════════════════════════════════════════════════════════
-- STEP 1: Drop deprecated tables (order matters for FK constraints)
-- ═══════════════════════════════════════════════════════════════════

-- Drop subscription_tier_allocations first (depends on subscriptions + device_tiers)
DROP TABLE IF EXISTS subscription_tier_allocations CASCADE;

-- Drop plan_tier_defaults (depends on subscription_plans + device_tiers)
DROP TABLE IF EXISTS plan_tier_defaults CASCADE;

-- Drop old subscriptions (will be replaced by device_subscriptions)
DROP TABLE IF EXISTS subscriptions CASCADE;

-- Drop subscription_plans
DROP TABLE IF EXISTS subscription_plans CASCADE;

-- Drop device_tiers
DROP TABLE IF EXISTS device_tiers CASCADE;

-- Drop old tenant_subscription if it still lingers from migration 029
DROP TABLE IF EXISTS tenant_subscription CASCADE;

-- ═══════════════════════════════════════════════════════════════════
-- STEP 2: Create account_tiers (per-tenant product definition)
-- ═══════════════════════════════════════════════════════════════════

-- RLS: EXEMPT - global account tier catalog metadata
CREATE TABLE account_tiers (
    tier_id             VARCHAR(50)     PRIMARY KEY,
    name                VARCHAR(100)    NOT NULL,
    description         TEXT            NOT NULL DEFAULT '',
    limits              JSONB           NOT NULL DEFAULT '{}',
    features            JSONB           NOT NULL DEFAULT '{}',
    support             JSONB           NOT NULL DEFAULT '{}',
    monthly_price_cents INT             NOT NULL DEFAULT 0,
    annual_price_cents  INT             NOT NULL DEFAULT 0,
    stripe_price_id     VARCHAR(100),
    stripe_annual_price_id VARCHAR(100),
    is_active           BOOLEAN         NOT NULL DEFAULT true,
    sort_order          INT             NOT NULL DEFAULT 0,
    created_at          TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE account_tiers IS 'Per-tenant product tier: shared resource limits, account-level features, support/SLA, base platform fee';
COMMENT ON COLUMN account_tiers.limits IS 'Numeric caps for shared resources: users, alert_rules, notification_channels, dashboards_per_user, device_groups, api_requests_per_minute';
COMMENT ON COLUMN account_tiers.features IS 'Boolean feature flags: sso, custom_branding, audit_log_export, bulk_device_import, carrier_self_service, alert_escalation, oncall_scheduling, maintenance_windows';
COMMENT ON COLUMN account_tiers.support IS 'Support definition: level (developer|standard|business|enterprise), sla_uptime_pct, response_time_hours, dedicated_csm';

-- ═══════════════════════════════════════════════════════════════════
-- STEP 3: Create device_plans (per-device product definition)
-- ═══════════════════════════════════════════════════════════════════

-- RLS: EXEMPT - global device plan catalog metadata
CREATE TABLE device_plans (
    plan_id             VARCHAR(50)     PRIMARY KEY,
    name                VARCHAR(100)    NOT NULL,
    description         TEXT            NOT NULL DEFAULT '',
    limits              JSONB           NOT NULL DEFAULT '{}',
    features            JSONB           NOT NULL DEFAULT '{}',
    monthly_price_cents INT             NOT NULL DEFAULT 0,
    annual_price_cents  INT             NOT NULL DEFAULT 0,
    stripe_price_id     VARCHAR(100),
    stripe_annual_price_id VARCHAR(100),
    is_active           BOOLEAN         NOT NULL DEFAULT true,
    sort_order          INT             NOT NULL DEFAULT 0,
    created_at          TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE device_plans IS 'Per-device/gateway product plan: device capability limits, per-device features, per-device pricing';
COMMENT ON COLUMN device_plans.limits IS 'Numeric caps per device: sensors, data_retention_days, telemetry_rate_per_minute, health_telemetry_interval_seconds';
COMMENT ON COLUMN device_plans.features IS 'Boolean feature flags per device: ota_updates, advanced_analytics, streaming_export, x509_auth, message_routing, device_commands, device_twin, carrier_diagnostics';

-- ═══════════════════════════════════════════════════════════════════
-- STEP 4: Create device_subscriptions (1 per device, billing lifecycle)
-- ═══════════════════════════════════════════════════════════════════

CREATE TABLE device_subscriptions (
    subscription_id     TEXT            PRIMARY KEY,
    tenant_id           TEXT            NOT NULL,
    device_id           TEXT            NOT NULL,
    plan_id             VARCHAR(50)     NOT NULL REFERENCES device_plans(plan_id),
    status              TEXT            NOT NULL DEFAULT 'ACTIVE'
                                        CHECK (status IN ('TRIAL', 'ACTIVE', 'GRACE', 'SUSPENDED', 'EXPIRED', 'CANCELLED')),
    term_start          TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    term_end            TIMESTAMPTZ,
    grace_end           TIMESTAMPTZ,
    stripe_subscription_id VARCHAR(100),
    stripe_price_id     VARCHAR(100),
    cancelled_at        TIMESTAMPTZ,
    created_at          TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

-- Each device has at most one non-terminal subscription
CREATE UNIQUE INDEX uq_device_subscriptions_active
    ON device_subscriptions (device_id)
    WHERE status NOT IN ('EXPIRED', 'CANCELLED');

CREATE INDEX idx_device_subscriptions_tenant ON device_subscriptions (tenant_id);
CREATE INDEX idx_device_subscriptions_status ON device_subscriptions (tenant_id, status);
CREATE INDEX idx_device_subscriptions_stripe ON device_subscriptions (stripe_subscription_id) WHERE stripe_subscription_id IS NOT NULL;

COMMENT ON TABLE device_subscriptions IS 'Per-device billing lifecycle: links one device to one device_plan with Stripe subscription tracking';

-- RLS
ALTER TABLE device_subscriptions ENABLE ROW LEVEL SECURITY;
CREATE POLICY device_subscriptions_tenant_isolation ON device_subscriptions
    USING (tenant_id = current_setting('app.tenant_id', true));

-- ═══════════════════════════════════════════════════════════════════
-- STEP 5: Alter tenants — add account_tier_id
-- ═══════════════════════════════════════════════════════════════════

ALTER TABLE tenants ADD COLUMN IF NOT EXISTS account_tier_id VARCHAR(50) REFERENCES account_tiers(tier_id);

-- Deprecate old columns (keep for now, drop in future migration)
-- tenants.support_tier — replaced by account_tiers.support.level
-- tenants.sla_level — replaced by account_tiers.support.sla_uptime_pct

-- ═══════════════════════════════════════════════════════════════════
-- STEP 6: Alter device_registry — add plan_id for quick lookup
-- ═══════════════════════════════════════════════════════════════════

-- Drop old tier_id FK if it exists (device_tiers table is being dropped)
ALTER TABLE device_registry DROP CONSTRAINT IF EXISTS device_registry_tier_id_fkey;
ALTER TABLE device_registry DROP COLUMN IF EXISTS tier_id;

-- Add plan_id for direct plan lookup (denormalized from device_subscriptions for query convenience)
ALTER TABLE device_registry ADD COLUMN IF NOT EXISTS plan_id VARCHAR(50) REFERENCES device_plans(plan_id);

-- ═══════════════════════════════════════════════════════════════════
-- STEP 7: Carrier permissions (was planned as separate migration 107)
-- ═══════════════════════════════════════════════════════════════════

INSERT INTO permissions (action, category, description) VALUES
    ('carrier.integrations.read',   'carrier', 'View carrier integrations'),
    ('carrier.integrations.write',  'carrier', 'Create/update/delete carrier integrations'),
    ('carrier.actions.execute',     'carrier', 'Execute remote carrier actions (activate, suspend, reboot)'),
    ('carrier.links.write',         'carrier', 'Link/unlink devices to carrier integrations')
ON CONFLICT (action) DO NOTHING;

-- Grant carrier permissions to Full Admin
DO $$
DECLARE
    v_role_id UUID;
BEGIN
    SELECT id INTO v_role_id FROM roles WHERE tenant_id IS NULL AND name = 'Full Admin' AND is_system = true;
    IF v_role_id IS NOT NULL THEN
        INSERT INTO role_permissions (role_id, permission_id)
        SELECT v_role_id, p.id FROM permissions p
        WHERE p.category = 'carrier'
          AND p.id NOT IN (SELECT permission_id FROM role_permissions WHERE role_id = v_role_id)
        ON CONFLICT DO NOTHING;
    END IF;

    SELECT id INTO v_role_id FROM roles WHERE tenant_id IS NULL AND name = 'Device Manager' AND is_system = true;
    IF v_role_id IS NOT NULL THEN
        INSERT INTO role_permissions (role_id, permission_id)
        SELECT v_role_id, p.id FROM permissions p
        WHERE p.category = 'carrier'
          AND p.id NOT IN (SELECT permission_id FROM role_permissions WHERE role_id = v_role_id)
        ON CONFLICT DO NOTHING;
    END IF;
END $$;

COMMIT;
