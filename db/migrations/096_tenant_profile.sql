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

