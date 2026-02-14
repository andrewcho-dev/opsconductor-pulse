-- Migration 070: Unify notification pipeline
-- Extends notification_channels to absorb integrations system
-- Adds notification_jobs for reliable queued delivery
-- Adds full routing fields to notification_routing_rules
-- Does NOT modify or drop integrations/delivery_jobs tables

DO $$
BEGIN
  IF EXISTS (
    SELECT 1
    FROM information_schema.constraint_column_usage
    WHERE table_name = 'notification_channels'
      AND column_name = 'channel_type'
      AND constraint_name LIKE '%check%'
  ) THEN
    EXECUTE (
      SELECT 'ALTER TABLE notification_channels DROP CONSTRAINT ' || constraint_name
      FROM information_schema.table_constraints
      WHERE table_name = 'notification_channels'
        AND constraint_type = 'CHECK'
        AND constraint_name LIKE '%channel_type%'
      LIMIT 1
    );
  END IF;
END$$;

ALTER TABLE notification_routing_rules
  ADD COLUMN IF NOT EXISTS site_ids TEXT[] DEFAULT NULL,
  ADD COLUMN IF NOT EXISTS device_prefixes TEXT[] DEFAULT NULL,
  ADD COLUMN IF NOT EXISTS deliver_on TEXT[] DEFAULT ARRAY['OPEN']::TEXT[],
  ADD COLUMN IF NOT EXISTS priority INTEGER DEFAULT 100;

CREATE TABLE IF NOT EXISTS notification_jobs (
    job_id            BIGSERIAL PRIMARY KEY,
    tenant_id         TEXT NOT NULL,
    alert_id          BIGINT NOT NULL,
    channel_id        INTEGER NOT NULL REFERENCES notification_channels(channel_id) ON DELETE CASCADE,
    rule_id           INTEGER REFERENCES notification_routing_rules(rule_id) ON DELETE SET NULL,
    deliver_on_event  TEXT NOT NULL DEFAULT 'OPEN'
        CHECK (deliver_on_event IN ('OPEN', 'CLOSED', 'ACKNOWLEDGED')),
    status            TEXT NOT NULL DEFAULT 'PENDING'
        CHECK (status IN ('PENDING', 'PROCESSING', 'COMPLETED', 'FAILED')),
    attempts          INTEGER NOT NULL DEFAULT 0,
    next_run_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_error        TEXT,
    payload_json      JSONB NOT NULL DEFAULT '{}',
    created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at        TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX IF NOT EXISTS notification_jobs_dedup_idx
    ON notification_jobs(tenant_id, alert_id, channel_id, deliver_on_event);

CREATE INDEX IF NOT EXISTS notification_jobs_poll_idx
    ON notification_jobs(status, next_run_at)
    WHERE status IN ('PENDING', 'PROCESSING');

ALTER TABLE notification_log
  ADD COLUMN IF NOT EXISTS job_id BIGINT REFERENCES notification_jobs(job_id) ON DELETE SET NULL,
  ADD COLUMN IF NOT EXISTS success BOOLEAN DEFAULT TRUE,
  ADD COLUMN IF NOT EXISTS error_msg TEXT;

GRANT SELECT, INSERT, UPDATE, DELETE ON notification_jobs TO pulse_app;
GRANT USAGE, SELECT ON SEQUENCE notification_jobs_job_id_seq TO pulse_app;
GRANT SELECT, INSERT, UPDATE ON notification_log TO pulse_app;
