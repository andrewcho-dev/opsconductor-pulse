-- Subscription entitlements and audit trail
CREATE TABLE IF NOT EXISTS tenant_subscription (
  tenant_id TEXT PRIMARY KEY REFERENCES tenants(tenant_id),
  device_limit INT NOT NULL DEFAULT 0,
  active_device_count INT NOT NULL DEFAULT 0,
  term_start TIMESTAMPTZ,
  term_end TIMESTAMPTZ,
  plan_id TEXT,
  status TEXT NOT NULL DEFAULT 'ACTIVE'
    CHECK (status IN ('TRIAL', 'ACTIVE', 'GRACE', 'SUSPENDED', 'EXPIRED')),
  grace_end TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS subscription_audit (
  id BIGSERIAL PRIMARY KEY,
  tenant_id TEXT NOT NULL REFERENCES tenants(tenant_id),
  event_type TEXT NOT NULL,
  event_timestamp TIMESTAMPTZ NOT NULL DEFAULT now(),
  actor_type TEXT,
  actor_id TEXT,
  previous_state JSONB,
  new_state JSONB,
  details JSONB,
  ip_address INET,
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_subscription_audit_tenant
  ON subscription_audit(tenant_id, event_timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_subscription_audit_type
  ON subscription_audit(event_type, event_timestamp DESC);

CREATE TABLE IF NOT EXISTS subscription_notifications (
  id BIGSERIAL PRIMARY KEY,
  tenant_id TEXT NOT NULL REFERENCES tenants(tenant_id),
  notification_type TEXT NOT NULL,
  scheduled_at TIMESTAMPTZ NOT NULL,
  sent_at TIMESTAMPTZ,
  channel TEXT,
  status TEXT DEFAULT 'PENDING',
  error TEXT,
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_subscription_notifications_pending
  ON subscription_notifications(scheduled_at)
  WHERE status = 'PENDING';

-- RLS policies
ALTER TABLE tenant_subscription ENABLE ROW LEVEL SECURITY;
ALTER TABLE subscription_audit ENABLE ROW LEVEL SECURITY;
ALTER TABLE subscription_notifications ENABLE ROW LEVEL SECURITY;

CREATE POLICY tenant_subscription_read ON tenant_subscription
  FOR SELECT USING (tenant_id = current_setting('app.tenant_id', true));

CREATE POLICY subscription_service_read ON tenant_subscription
  FOR SELECT TO iot USING (true);

CREATE POLICY subscription_audit_read ON subscription_audit
  FOR SELECT USING (tenant_id = current_setting('app.tenant_id', true));

-- Grants
GRANT ALL ON tenant_subscription TO pulse_operator;
GRANT ALL ON subscription_audit TO pulse_operator;
GRANT ALL ON subscription_notifications TO pulse_operator;

GRANT SELECT ON tenant_subscription TO pulse_app;
GRANT SELECT ON subscription_audit TO pulse_app;
GRANT SELECT ON tenant_subscription TO iot;

-- Seed existing tenants with a default subscription
INSERT INTO tenant_subscription (tenant_id, device_limit, status, term_start, term_end)
SELECT
  tenant_id,
  1000,
  'ACTIVE',
  now(),
  now() + interval '1 year'
FROM tenants
WHERE status = 'ACTIVE'
ON CONFLICT (tenant_id) DO NOTHING;
