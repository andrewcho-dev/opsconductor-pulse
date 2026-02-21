# 001: Database Migration for Multi-Subscription

## Task

Create database migration to support multiple subscriptions per tenant with device-level subscription assignment.

## File to Create

`db/migrations/030_multi_subscription.sql`

## Schema

### 1. Create subscriptions table

```sql
-- Subscriptions table (replaces tenant_subscription for new model)
CREATE TABLE subscriptions (
  subscription_id TEXT PRIMARY KEY,  -- Format: SUB-YYYYMMDD-XXXXX
  tenant_id TEXT NOT NULL REFERENCES tenants(tenant_id),

  -- Subscription type and hierarchy
  subscription_type TEXT NOT NULL CHECK (subscription_type IN ('MAIN', 'ADDON', 'TRIAL', 'TEMPORARY')),
  parent_subscription_id TEXT REFERENCES subscriptions(subscription_id),

  -- Capacity
  device_limit INT NOT NULL DEFAULT 0,
  active_device_count INT NOT NULL DEFAULT 0,

  -- Term
  term_start TIMESTAMPTZ NOT NULL,
  term_end TIMESTAMPTZ NOT NULL,

  -- Status
  status TEXT NOT NULL DEFAULT 'ACTIVE' CHECK (status IN ('TRIAL', 'ACTIVE', 'GRACE', 'SUSPENDED', 'EXPIRED')),
  grace_end TIMESTAMPTZ,

  -- Metadata
  plan_id TEXT,
  description TEXT,  -- e.g., "Q4 2024 Expansion", "Trade Show Demo"

  -- Audit
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now(),
  created_by TEXT,  -- operator who created

  -- Constraints
  CONSTRAINT addon_requires_parent CHECK (
    (subscription_type = 'ADDON' AND parent_subscription_id IS NOT NULL) OR
    (subscription_type != 'ADDON')
  ),
  CONSTRAINT main_no_parent CHECK (
    (subscription_type = 'MAIN' AND parent_subscription_id IS NULL) OR
    (subscription_type != 'MAIN')
  )
);

-- Indexes
CREATE INDEX idx_subscriptions_tenant ON subscriptions(tenant_id, status);
CREATE INDEX idx_subscriptions_parent ON subscriptions(parent_subscription_id) WHERE parent_subscription_id IS NOT NULL;
CREATE INDEX idx_subscriptions_expiring ON subscriptions(term_end) WHERE status IN ('ACTIVE', 'TRIAL');
```

### 2. Add subscription_id to device_registry

```sql
-- Add subscription reference to devices
ALTER TABLE device_registry
  ADD COLUMN subscription_id TEXT REFERENCES subscriptions(subscription_id);

-- Index for subscription lookups
CREATE INDEX idx_device_subscription ON device_registry(subscription_id) WHERE subscription_id IS NOT NULL;
```

### 3. Create subscription_devices view (convenience)

```sql
-- View showing devices with their subscription info
CREATE OR REPLACE VIEW subscription_devices AS
SELECT
  d.tenant_id,
  d.device_id,
  d.site_id,
  d.status as device_status,
  s.subscription_id,
  s.subscription_type,
  s.status as subscription_status,
  s.term_end,
  s.device_limit,
  s.active_device_count
FROM device_registry d
LEFT JOIN subscriptions s ON d.subscription_id = s.subscription_id;
```

### 4. Function to generate subscription IDs

```sql
-- Generate unique subscription ID
CREATE OR REPLACE FUNCTION generate_subscription_id() RETURNS TEXT AS $$
DECLARE
  today TEXT;
  seq INT;
  new_id TEXT;
BEGIN
  today := to_char(now(), 'YYYYMMDD');

  -- Get next sequence for today
  SELECT COALESCE(MAX(
    CAST(SUBSTRING(subscription_id FROM 14 FOR 5) AS INT)
  ), 0) + 1
  INTO seq
  FROM subscriptions
  WHERE subscription_id LIKE 'SUB-' || today || '-%';

  new_id := 'SUB-' || today || '-' || LPAD(seq::TEXT, 5, '0');
  RETURN new_id;
END;
$$ LANGUAGE plpgsql;
```

### 5. Trigger to sync ADDON term_end with parent

```sql
-- Keep ADDON subscriptions coterminous with parent
CREATE OR REPLACE FUNCTION sync_addon_term_end() RETURNS TRIGGER AS $$
BEGIN
  IF NEW.subscription_type = 'ADDON' AND NEW.parent_subscription_id IS NOT NULL THEN
    SELECT term_end INTO NEW.term_end
    FROM subscriptions
    WHERE subscription_id = NEW.parent_subscription_id;
  END IF;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_sync_addon_term
  BEFORE INSERT OR UPDATE ON subscriptions
  FOR EACH ROW
  WHEN (NEW.subscription_type = 'ADDON')
  EXECUTE FUNCTION sync_addon_term_end();

-- Also update ADDONs when parent term_end changes
CREATE OR REPLACE FUNCTION cascade_term_end_to_addons() RETURNS TRIGGER AS $$
BEGIN
  IF NEW.term_end != OLD.term_end THEN
    UPDATE subscriptions
    SET term_end = NEW.term_end, updated_at = now()
    WHERE parent_subscription_id = NEW.subscription_id
      AND subscription_type = 'ADDON';
  END IF;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_cascade_term_end
  AFTER UPDATE ON subscriptions
  FOR EACH ROW
  WHEN (OLD.subscription_type = 'MAIN')
  EXECUTE FUNCTION cascade_term_end_to_addons();
```

### 6. RLS Policies

```sql
-- Enable RLS
ALTER TABLE subscriptions ENABLE ROW LEVEL SECURITY;

-- Customers can see their own subscriptions
CREATE POLICY subscriptions_customer_read ON subscriptions
  FOR SELECT TO pulse_app
  USING (tenant_id = current_setting('app.tenant_id', true));

-- Operators can see all
CREATE POLICY subscriptions_operator_all ON subscriptions
  FOR ALL TO pulse_operator
  USING (true) WITH CHECK (true);

-- Service role (ingest) can read all for device checks
CREATE POLICY subscriptions_service_read ON subscriptions
  FOR SELECT TO iot
  USING (true);
```

### 7. Grants

```sql
GRANT SELECT ON subscriptions TO pulse_app;
GRANT ALL ON subscriptions TO pulse_operator;
GRANT SELECT ON subscriptions TO iot;
GRANT SELECT ON subscription_devices TO pulse_app;
GRANT SELECT ON subscription_devices TO pulse_operator;
```

### 8. Keep old table for backward compatibility (temporary)

```sql
-- Don't drop tenant_subscription yet - migration script will handle data
-- Add deprecation comment
COMMENT ON TABLE tenant_subscription IS 'DEPRECATED: Use subscriptions table instead. Will be removed after data migration.';
```

## Verification

```sql
-- Test subscription ID generation
SELECT generate_subscription_id();  -- Should return SUB-YYYYMMDD-00001

-- Test ADDON coterminous constraint
INSERT INTO subscriptions (subscription_id, tenant_id, subscription_type, device_limit, term_start, term_end)
VALUES ('SUB-TEST-MAIN', 'tenant-a', 'MAIN', 50, now(), now() + interval '1 year');

INSERT INTO subscriptions (subscription_id, tenant_id, subscription_type, parent_subscription_id, device_limit, term_start, term_end)
VALUES ('SUB-TEST-ADDON', 'tenant-a', 'ADDON', 'SUB-TEST-MAIN', 10, now(), now() + interval '1 year');

-- Verify ADDON term_end matches MAIN
SELECT subscription_id, subscription_type, term_end FROM subscriptions WHERE subscription_id LIKE 'SUB-TEST-%';

-- Update MAIN term_end, verify ADDON updates
UPDATE subscriptions SET term_end = now() + interval '2 years' WHERE subscription_id = 'SUB-TEST-MAIN';
SELECT subscription_id, subscription_type, term_end FROM subscriptions WHERE subscription_id LIKE 'SUB-TEST-%';
```
