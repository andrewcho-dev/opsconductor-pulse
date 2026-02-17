-- Migration 097: Device tiers and subscription tier allocations

-- 1. Device tiers (platform-wide, not tenant-scoped)
CREATE TABLE IF NOT EXISTS device_tiers (
    tier_id     SERIAL PRIMARY KEY,
    name        VARCHAR(50) NOT NULL UNIQUE,       -- 'basic', 'standard', 'premium'
    display_name VARCHAR(100) NOT NULL,             -- 'Basic', 'Standard', 'Premium'
    description TEXT DEFAULT '',
    features    JSONB NOT NULL DEFAULT '{}',        -- {"telemetry": true, "ota": false, ...}
    sort_order  INT NOT NULL DEFAULT 0,             -- for UI ordering
    is_active   BOOLEAN NOT NULL DEFAULT true,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- No RLS on device_tiers (platform-wide reference table)
GRANT SELECT ON device_tiers TO pulse_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON device_tiers TO pulse_operator;
GRANT USAGE, SELECT ON SEQUENCE device_tiers_tier_id_seq TO pulse_operator;

-- 2. Seed default tiers
INSERT INTO device_tiers (name, display_name, description, features, sort_order) VALUES
(
    'basic',
    'Basic',
    'Telemetry ingestion, alerting, and dashboard visibility',
    '{"telemetry": true, "alerts": true, "dashboards": true, "ota": false, "analytics": false, "x509_auth": false, "streaming_export": false, "message_routing": false}'::jsonb,
    1
),
(
    'standard',
    'Standard',
    'Everything in Basic plus OTA updates, analytics, and streaming export',
    '{"telemetry": true, "alerts": true, "dashboards": true, "ota": true, "analytics": true, "x509_auth": false, "streaming_export": true, "message_routing": false}'::jsonb,
    2
),
(
    'premium',
    'Premium',
    'Full platform capabilities including X.509 certificates and message routing',
    '{"telemetry": true, "alerts": true, "dashboards": true, "ota": true, "analytics": true, "x509_auth": true, "streaming_export": true, "message_routing": true}'::jsonb,
    3
)
ON CONFLICT (name) DO NOTHING;

-- 3. Add tier_id to device_registry
ALTER TABLE device_registry ADD COLUMN IF NOT EXISTS tier_id INT REFERENCES device_tiers(tier_id);

CREATE INDEX IF NOT EXISTS idx_device_tier ON device_registry(tier_id) WHERE tier_id IS NOT NULL;

-- 4. Subscription tier allocations (how many slots of each tier a subscription includes)
CREATE TABLE IF NOT EXISTS subscription_tier_allocations (
    id              SERIAL PRIMARY KEY,
    subscription_id TEXT NOT NULL REFERENCES subscriptions(subscription_id) ON DELETE CASCADE,
    tier_id         INT NOT NULL REFERENCES device_tiers(tier_id),
    slot_limit      INT NOT NULL DEFAULT 0,       -- max devices of this tier
    slots_used      INT NOT NULL DEFAULT 0,       -- current count
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    UNIQUE (subscription_id, tier_id),
    CONSTRAINT slots_used_non_negative CHECK (slots_used >= 0),
    CONSTRAINT slots_limit_non_negative CHECK (slot_limit >= 0)
);

-- RLS: subscription_tier_allocations inherits tenant scope via subscription join
-- For simplicity, use operator-only direct access; customer access goes through subscription endpoints
GRANT SELECT ON subscription_tier_allocations TO pulse_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON subscription_tier_allocations TO pulse_operator;
GRANT USAGE, SELECT ON SEQUENCE subscription_tier_allocations_id_seq TO pulse_operator;
GRANT USAGE, SELECT ON SEQUENCE subscription_tier_allocations_id_seq TO pulse_app;

-- 5. Add stripe_subscription_id to subscriptions table
ALTER TABLE subscriptions ADD COLUMN IF NOT EXISTS stripe_subscription_id VARCHAR(100);
ALTER TABLE subscriptions ADD COLUMN IF NOT EXISTS stripe_price_id VARCHAR(100);

CREATE INDEX IF NOT EXISTS idx_subscriptions_stripe ON subscriptions(stripe_subscription_id)
    WHERE stripe_subscription_id IS NOT NULL;

-- 6. Subscription plans (database-driven — NO hardcoded plan names/limits in code)
CREATE TABLE IF NOT EXISTS subscription_plans (
    plan_id             VARCHAR(50) PRIMARY KEY,        -- 'starter', 'pro', 'enterprise'
    name                VARCHAR(100) NOT NULL,           -- 'Starter', 'Pro', 'Enterprise'
    description         TEXT DEFAULT '',
    device_limit        INT NOT NULL DEFAULT 0,          -- max total devices for the plan
    limits              JSONB NOT NULL DEFAULT '{}',     -- {"alert_rules": 25, "notification_channels": 5, "users": 5}
    stripe_price_id     VARCHAR(100),                    -- Stripe monthly price ID (source of truth for pricing is Stripe)
    stripe_annual_price_id VARCHAR(100),                 -- Stripe annual price ID
    monthly_price_cents INT,                             -- for display only (Stripe is authoritative)
    annual_price_cents  INT,                             -- for display only
    is_active           BOOLEAN NOT NULL DEFAULT true,
    sort_order          INT NOT NULL DEFAULT 0,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

GRANT SELECT ON subscription_plans TO pulse_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON subscription_plans TO pulse_operator;

-- Seed default plans (Stripe price IDs from sandbox)
INSERT INTO subscription_plans (plan_id, name, description, device_limit, limits,
    stripe_price_id, stripe_annual_price_id, monthly_price_cents, annual_price_cents, sort_order) VALUES
(
    'starter',
    'Starter',
    'For small teams getting started with IoT monitoring',
    30,
    '{"alert_rules": 25, "notification_channels": 5, "users": 5}'::jsonb,
    'price_1T1dEjHrKfyMPrqMUkIOo3UP',  -- $29/month
    'price_1T1dEjHrKfyMPrqMzqsVCj8m',  -- $290/year
    2900,
    29000,
    1
),
(
    'pro',
    'Pro',
    'For growing teams with advanced analytics and OTA updates',
    260,
    '{"alert_rules": 200, "notification_channels": 25, "users": 25}'::jsonb,
    'price_1T1dJMHrKfyMPrqMlSoB8sp9',  -- $99/month
    'price_1T1dJMHrKfyMPrqMFlCT7QFg',  -- $990/year
    9900,
    99000,
    2
),
(
    'enterprise',
    'Enterprise',
    'Full platform capabilities with dedicated support',
    16000,
    '{"alert_rules": 10000, "notification_channels": 100, "users": 500}'::jsonb,
    'price_1T1dKyHrKfyMPrqMmFgrQjtX',  -- $499/month
    'price_1T1dKyHrKfyMPrqMeEDHr7xu',  -- $4990/year
    49900,
    499000,
    3
)
ON CONFLICT (plan_id) DO NOTHING;

-- 7. Plan-to-tier default allocations (what tier slots each plan includes)
CREATE TABLE IF NOT EXISTS plan_tier_defaults (
    id          SERIAL PRIMARY KEY,
    plan_id     VARCHAR(50) NOT NULL REFERENCES subscription_plans(plan_id) ON DELETE CASCADE,
    tier_id     INT NOT NULL REFERENCES device_tiers(tier_id),
    slot_limit  INT NOT NULL DEFAULT 0,
    UNIQUE (plan_id, tier_id)
);

GRANT SELECT ON plan_tier_defaults TO pulse_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON plan_tier_defaults TO pulse_operator;
GRANT USAGE, SELECT ON SEQUENCE plan_tier_defaults_id_seq TO pulse_operator;

-- Seed default plan tier allocations
INSERT INTO plan_tier_defaults (plan_id, tier_id, slot_limit) VALUES
    ('starter',    1, 25),    -- 25 Basic
    ('starter',    2, 5),     -- 5 Standard
    ('starter',    3, 0),     -- 0 Premium
    ('pro',        1, 200),   -- 200 Basic
    ('pro',        2, 50),    -- 50 Standard
    ('pro',        3, 10),    -- 10 Premium
    ('enterprise', 1, 10000), -- 10000 Basic (effectively unlimited)
    ('enterprise', 2, 5000),  -- 5000 Standard
    ('enterprise', 3, 1000)   -- 1000 Premium
ON CONFLICT (plan_id, tier_id) DO NOTHING;

