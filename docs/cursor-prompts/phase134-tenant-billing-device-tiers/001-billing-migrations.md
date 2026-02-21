# 001 -- DB Migrations: Tenant Profile Enrichment + Device Tiers + RLS

## Context

The `tenants` table (migration 018) has only: tenant_id, name, status, contact_email, contact_name, metadata, timestamps. Enterprise IoT platforms store company address, industry, data residency region, support tier, and Stripe billing linkage. The `device_registry` has no concept of device tiers/classes. Customers cannot read their own tenant row (RLS blocks `pulse_app`).

## Task

### Migration 096: Tenant Profile Enrichment

Create `db/migrations/096_tenant_profile.sql`:

```sql
-- Migration 096: Enrich tenants table with company profile and billing fields

-- Company profile
ALTER TABLE tenants ADD COLUMN IF NOT EXISTS legal_name VARCHAR(200);
ALTER TABLE tenants ADD COLUMN IF NOT EXISTS phone VARCHAR(50);
ALTER TABLE tenants ADD COLUMN IF NOT EXISTS industry VARCHAR(100);
ALTER TABLE tenants ADD COLUMN IF NOT EXISTS company_size VARCHAR(50);  -- '1-10', '11-50', '51-200', '201-500', '501-1000', '1000+'

-- Address
ALTER TABLE tenants ADD COLUMN IF NOT EXISTS address_line1 VARCHAR(200);
ALTER TABLE tenants ADD COLUMN IF NOT EXISTS address_line2 VARCHAR(200);
ALTER TABLE tenants ADD COLUMN IF NOT EXISTS city VARCHAR(100);
ALTER TABLE tenants ADD COLUMN IF NOT EXISTS state_province VARCHAR(100);
ALTER TABLE tenants ADD COLUMN IF NOT EXISTS postal_code VARCHAR(20);
ALTER TABLE tenants ADD COLUMN IF NOT EXISTS country VARCHAR(2);  -- ISO 3166-1 alpha-2

-- Compliance & operations
ALTER TABLE tenants ADD COLUMN IF NOT EXISTS data_residency_region VARCHAR(50);  -- 'us-east', 'eu-west', 'ap-southeast', etc.
ALTER TABLE tenants ADD COLUMN IF NOT EXISTS support_tier VARCHAR(20) DEFAULT 'standard';  -- 'developer', 'standard', 'business', 'enterprise'
ALTER TABLE tenants ADD COLUMN IF NOT EXISTS sla_level NUMERIC(5,2);  -- e.g. 99.90, 99.99

-- Stripe billing linkage
ALTER TABLE tenants ADD COLUMN IF NOT EXISTS stripe_customer_id VARCHAR(100) UNIQUE;
ALTER TABLE tenants ADD COLUMN IF NOT EXISTS billing_email VARCHAR(255);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_tenants_stripe ON tenants(stripe_customer_id) WHERE stripe_customer_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_tenants_industry ON tenants(industry) WHERE industry IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_tenants_country ON tenants(country) WHERE country IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_tenants_region ON tenants(data_residency_region) WHERE data_residency_region IS NOT NULL;

-- RLS: Allow customers to read their own tenant row
-- (tenants table currently only allows pulse_operator via BYPASSRLS)
CREATE POLICY tenants_self_read ON tenants
    FOR SELECT TO pulse_app
    USING (tenant_id = current_setting('app.tenant_id', true));

CREATE POLICY tenants_self_update ON tenants
    FOR UPDATE TO pulse_app
    USING (tenant_id = current_setting('app.tenant_id', true))
    WITH CHECK (tenant_id = current_setting('app.tenant_id', true));

-- Grant SELECT + UPDATE to pulse_app (may already have SELECT from migration 018)
GRANT SELECT, UPDATE ON tenants TO pulse_app;
```

### Migration 097: Device Tiers + Subscription Tier Allocations

Create `db/migrations/097_device_tiers.sql`:

```sql
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
```

## Verify

```bash
# Run migrations
docker compose -f compose/docker-compose.yml exec ui python -m scripts.migrate

# Check tenants table has new columns
docker compose -f compose/docker-compose.yml exec db psql -U iot -d pulse \
  -c "\d tenants" | grep -E "stripe|billing|industry|address|country|region|support"

# Check RLS policies
docker compose -f compose/docker-compose.yml exec db psql -U iot -d pulse \
  -c "SELECT policyname, cmd FROM pg_policies WHERE tablename = 'tenants'"

# Check device_tiers seeded
docker compose -f compose/docker-compose.yml exec db psql -U iot -d pulse \
  -c "SELECT tier_id, name, display_name FROM device_tiers ORDER BY sort_order"

# Check plan_tier_defaults seeded
docker compose -f compose/docker-compose.yml exec db psql -U iot -d pulse \
  -c "SELECT plan_id, t.name, ptd.slot_limit FROM plan_tier_defaults ptd JOIN device_tiers t ON t.tier_id = ptd.tier_id ORDER BY plan_id, t.sort_order"
```

## Commit

```
feat(phase134): add tenant profile, device tier, and billing migrations

Migration 096: Enrich tenants table with company address, industry,
data residency, support tier, Stripe customer ID, billing email.
Add RLS policies for customer self-read/update of own tenant row.

Migration 097: Create device_tiers with Basic/Standard/Premium defaults,
add tier_id to device_registry, create subscription_tier_allocations,
add Stripe columns to subscriptions, create plan_tier_defaults with
starter/pro/enterprise slot allocations.
```
