-- Webhook Delivery v1 Migration
-- Idempotent: safe to run multiple times

CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- integrations: customer-configured webhook endpoints
CREATE TABLE IF NOT EXISTS integrations (
  tenant_id       TEXT NOT NULL,
  integration_id  UUID NOT NULL DEFAULT gen_random_uuid(),
  name            TEXT NOT NULL,
  type            TEXT NOT NULL DEFAULT 'webhook' CHECK (type IN ('webhook')),
  enabled         BOOLEAN NOT NULL DEFAULT true,
  config_json     JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (tenant_id, integration_id)
);

CREATE INDEX IF NOT EXISTS integrations_tenant_enabled_idx
ON integrations (tenant_id, enabled) WHERE enabled = true;

-- integration_routes: routing rules for alerts to integrations
CREATE TABLE IF NOT EXISTS integration_routes (
  tenant_id        TEXT NOT NULL,
  route_id         UUID NOT NULL DEFAULT gen_random_uuid(),
  integration_id   UUID NOT NULL,
  name             TEXT NOT NULL,
  enabled          BOOLEAN NOT NULL DEFAULT true,
  min_severity     INT NULL,
  alert_types      TEXT[] NULL,
  site_ids         TEXT[] NULL,
  device_prefixes  TEXT[] NULL,
  deliver_on       TEXT[] NOT NULL DEFAULT ARRAY['OPEN'],
  priority         INT NOT NULL DEFAULT 100,
  created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (tenant_id, route_id),
  FOREIGN KEY (tenant_id, integration_id) REFERENCES integrations (tenant_id, integration_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS integration_routes_tenant_enabled_idx
ON integration_routes (tenant_id, enabled) WHERE enabled = true;

CREATE INDEX IF NOT EXISTS integration_routes_integration_idx
ON integration_routes (tenant_id, integration_id);

-- delivery_jobs: work queue for webhook delivery
CREATE TABLE IF NOT EXISTS delivery_jobs (
  job_id           BIGSERIAL PRIMARY KEY,
  tenant_id        TEXT NOT NULL,
  alert_id         BIGINT NOT NULL,
  integration_id   UUID NOT NULL,
  route_id         UUID NOT NULL,
  deliver_on_event TEXT NOT NULL CHECK (deliver_on_event IN ('OPEN', 'CLOSED')),
  status           TEXT NOT NULL DEFAULT 'PENDING' CHECK (status IN ('PENDING', 'PROCESSING', 'COMPLETED', 'FAILED')),
  attempts         INT NOT NULL DEFAULT 0,
  next_run_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
  last_error       TEXT NULL,
  payload_json     JSONB NOT NULL,
  created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
  FOREIGN KEY (tenant_id, integration_id) REFERENCES integrations (tenant_id, integration_id) ON DELETE CASCADE,
  FOREIGN KEY (tenant_id, route_id) REFERENCES integration_routes (tenant_id, route_id) ON DELETE CASCADE
);

-- Prevent duplicate jobs for same alert+route+event
CREATE UNIQUE INDEX IF NOT EXISTS delivery_jobs_dedup_idx
ON delivery_jobs (tenant_id, alert_id, route_id, deliver_on_event);

-- Worker polling: pending jobs ordered by next_run_at
CREATE INDEX IF NOT EXISTS delivery_jobs_pending_idx
ON delivery_jobs (next_run_at, job_id)
WHERE status = 'PENDING';

-- Tenant filtering
CREATE INDEX IF NOT EXISTS delivery_jobs_tenant_status_idx
ON delivery_jobs (tenant_id, status, created_at DESC);

-- delivery_attempts: individual attempt records
CREATE TABLE IF NOT EXISTS delivery_attempts (
  attempt_id   BIGSERIAL PRIMARY KEY,
  tenant_id    TEXT NOT NULL,
  job_id       BIGINT NOT NULL REFERENCES delivery_jobs (job_id) ON DELETE CASCADE,
  attempt_no   INT NOT NULL,
  ok           BOOLEAN NOT NULL,
  http_status  INT NULL,
  latency_ms   INT NULL,
  error        TEXT NULL,
  started_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
  finished_at  TIMESTAMPTZ NULL
);

CREATE INDEX IF NOT EXISTS delivery_attempts_job_idx
ON delivery_attempts (job_id, attempt_no);

CREATE INDEX IF NOT EXISTS delivery_attempts_tenant_idx
ON delivery_attempts (tenant_id, finished_at DESC);

-- Shared trigger function for updated_at columns
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS integrations_updated_at_trigger ON integrations;
CREATE TRIGGER integrations_updated_at_trigger
    BEFORE UPDATE ON integrations
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS integration_routes_updated_at_trigger ON integration_routes;
CREATE TRIGGER integration_routes_updated_at_trigger
    BEFORE UPDATE ON integration_routes
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS delivery_jobs_updated_at_trigger ON delivery_jobs;
CREATE TRIGGER delivery_jobs_updated_at_trigger
    BEFORE UPDATE ON delivery_jobs
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
