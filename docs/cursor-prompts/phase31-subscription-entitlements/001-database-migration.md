# 001: Database Migration for Subscription Entitlements

## Task

Create the database migration file for the subscription and entitlement system.

## File to Create

`db/migrations/029_subscription_entitlements.sql`

## Schema Requirements

### 1. tenant_subscription table

```sql
CREATE TABLE tenant_subscription (
  tenant_id TEXT PRIMARY KEY REFERENCES tenants(tenant_id),
  device_limit INT NOT NULL DEFAULT 0,
  active_device_count INT NOT NULL DEFAULT 0,  -- denormalized for fast checks
  term_start TIMESTAMPTZ,
  term_end TIMESTAMPTZ,
  plan_id TEXT,
  status TEXT NOT NULL DEFAULT 'ACTIVE'
    CHECK (status IN ('TRIAL', 'ACTIVE', 'GRACE', 'SUSPENDED', 'EXPIRED')),
  grace_end TIMESTAMPTZ,  -- 14 days after term_end
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);
```

### 2. subscription_audit table

```sql
CREATE TABLE subscription_audit (
  id BIGSERIAL PRIMARY KEY,
  tenant_id TEXT NOT NULL REFERENCES tenants(tenant_id),
  event_type TEXT NOT NULL,  -- CREATED, RENEWED, UPGRADED, DOWNGRADED, DEVICE_ADDED,
                             -- DEVICE_REMOVED, LIMIT_CHANGED, PAYMENT_RECEIVED,
                             -- GRACE_STARTED, SUSPENDED, EXPIRED, REACTIVATED
  event_timestamp TIMESTAMPTZ NOT NULL DEFAULT now(),
  actor_type TEXT,  -- 'user', 'system', 'billing_webhook', 'admin'
  actor_id TEXT,
  previous_state JSONB,  -- snapshot before change
  new_state JSONB,       -- snapshot after change
  details JSONB,         -- additional context (invoice_id, amount, etc.)
  ip_address INET,
  created_at TIMESTAMPTZ DEFAULT now()
);
```

Indexes:
- `idx_subscription_audit_tenant ON subscription_audit(tenant_id, event_timestamp DESC)`
- `idx_subscription_audit_type ON subscription_audit(event_type, event_timestamp DESC)`

### 3. subscription_notifications table

```sql
CREATE TABLE subscription_notifications (
  id BIGSERIAL PRIMARY KEY,
  tenant_id TEXT NOT NULL REFERENCES tenants(tenant_id),
  notification_type TEXT NOT NULL,  -- RENEWAL_90, RENEWAL_60, RENEWAL_30, RENEWAL_14, RENEWAL_7, RENEWAL_1
                                    -- GRACE_START, GRACE_7, SUSPENDED, EXPIRED
  scheduled_at TIMESTAMPTZ NOT NULL,
  sent_at TIMESTAMPTZ,
  channel TEXT,  -- 'email', 'in_app', 'webhook'
  status TEXT DEFAULT 'PENDING',  -- PENDING, SENT, FAILED
  error TEXT,
  created_at TIMESTAMPTZ DEFAULT now()
);
```

Index:
- `idx_subscription_notifications_pending ON subscription_notifications(scheduled_at) WHERE status = 'PENDING'`

### 4. RLS Policies

Enable RLS on all three tables:

```sql
ALTER TABLE tenant_subscription ENABLE ROW LEVEL SECURITY;
ALTER TABLE subscription_audit ENABLE ROW LEVEL SECURITY;
ALTER TABLE subscription_notifications ENABLE ROW LEVEL SECURITY;

-- Tenants can read their own subscription
CREATE POLICY tenant_subscription_read ON tenant_subscription
  FOR SELECT USING (tenant_id = current_setting('app.tenant_id', true));

-- Tenants can read their own audit log
CREATE POLICY subscription_audit_read ON subscription_audit
  FOR SELECT USING (tenant_id = current_setting('app.tenant_id', true));
```

### 5. Grants

```sql
-- Operators can do everything
GRANT ALL ON tenant_subscription TO pulse_operator;
GRANT ALL ON subscription_audit TO pulse_operator;
GRANT ALL ON subscription_notifications TO pulse_operator;

-- App role can read own subscription
GRANT SELECT ON tenant_subscription TO pulse_app;
GRANT SELECT ON subscription_audit TO pulse_app;
```

### 6. Seed existing tenants

Add a subscription record for each existing tenant with generous defaults:

```sql
INSERT INTO tenant_subscription (tenant_id, device_limit, status, term_start, term_end)
SELECT
  tenant_id,
  1000,  -- generous default limit
  'ACTIVE',
  now(),
  now() + interval '1 year'
FROM tenants
WHERE status = 'ACTIVE'
ON CONFLICT (tenant_id) DO NOTHING;
```

## Reference

Look at existing migrations for style:
- `db/migrations/028_system_audit_log.sql` - audit log pattern
- `db/migrations/018_tenants_table.sql` - tenants table, RLS policies

## Validation

After creating the migration, verify it can be applied:

```bash
docker compose exec postgres psql -U iot -d iotcloud -f /path/to/029_subscription_entitlements.sql
```
