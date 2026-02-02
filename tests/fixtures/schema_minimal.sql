-- Minimal schema for test database (core tables not in migrations)

CREATE TABLE IF NOT EXISTS device_state (
  tenant_id            TEXT NOT NULL,
  site_id              TEXT NOT NULL,
  device_id            TEXT NOT NULL,
  status               TEXT NOT NULL,
  last_heartbeat_at    TIMESTAMPTZ NULL,
  last_telemetry_at    TIMESTAMPTZ NULL,
  last_seen_at         TIMESTAMPTZ NULL,
  last_state_change_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  state                JSONB NOT NULL DEFAULT '{}'::jsonb,
  PRIMARY KEY (tenant_id, device_id)
);

CREATE INDEX IF NOT EXISTS device_state_site_idx ON device_state (site_id);

CREATE TABLE IF NOT EXISTS fleet_alert (
  id          BIGSERIAL PRIMARY KEY,
  created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
  closed_at   TIMESTAMPTZ NULL,
  tenant_id   TEXT NOT NULL,
  site_id     TEXT NOT NULL,
  device_id   TEXT NOT NULL,
  alert_type  TEXT NOT NULL,
  fingerprint TEXT NOT NULL DEFAULT '',
  status      TEXT NOT NULL DEFAULT 'OPEN',
  severity    INTEGER NOT NULL DEFAULT 0,
  confidence  REAL NOT NULL DEFAULT 0.0,
  summary     TEXT NOT NULL,
  details     JSONB NOT NULL DEFAULT '{}'::jsonb
);

CREATE UNIQUE INDEX IF NOT EXISTS fleet_alert_open_uq
  ON fleet_alert (tenant_id, fingerprint) WHERE status = 'OPEN';

CREATE INDEX IF NOT EXISTS fleet_alert_site_idx ON fleet_alert (site_id, status);

CREATE TABLE IF NOT EXISTS raw_events (
  id          BIGSERIAL PRIMARY KEY,
  ingested_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  event_ts    TIMESTAMPTZ NULL,
  topic       TEXT NOT NULL,
  tenant_id   TEXT NULL,
  site_id     TEXT NULL,
  device_id   TEXT NULL,
  msg_type    TEXT NULL,
  payload     JSONB NOT NULL,
  accepted    BOOLEAN NOT NULL DEFAULT true
);

CREATE INDEX IF NOT EXISTS raw_events_accepted_idx ON raw_events (accepted, ingested_at DESC);
CREATE INDEX IF NOT EXISTS raw_events_device_idx ON raw_events (device_id);
CREATE INDEX IF NOT EXISTS raw_events_ingested_at_idx ON raw_events (ingested_at DESC);
CREATE INDEX IF NOT EXISTS raw_events_payload_gin_idx ON raw_events USING gin (payload);
CREATE INDEX IF NOT EXISTS raw_events_tenant_idx ON raw_events (tenant_id);

CREATE TABLE IF NOT EXISTS quarantine_events (
  id          BIGSERIAL PRIMARY KEY,
  ingested_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  event_ts    TIMESTAMPTZ NULL,
  topic       TEXT NOT NULL,
  tenant_id   TEXT NULL,
  site_id     TEXT NULL,
  device_id   TEXT NULL,
  msg_type    TEXT NULL,
  reason      TEXT NOT NULL,
  payload     JSONB NOT NULL
);

CREATE INDEX IF NOT EXISTS quarantine_device_idx ON quarantine_events (device_id);
CREATE INDEX IF NOT EXISTS quarantine_ingested_at_idx ON quarantine_events (ingested_at DESC);
CREATE INDEX IF NOT EXISTS quarantine_tenant_idx ON quarantine_events (tenant_id);

CREATE TABLE IF NOT EXISTS quarantine_counters_minute (
  bucket_minute TIMESTAMPTZ NOT NULL,
  tenant_id     TEXT NOT NULL,
  reason        TEXT NOT NULL,
  cnt           BIGINT NOT NULL DEFAULT 0,
  PRIMARY KEY (bucket_minute, tenant_id, reason)
);

CREATE INDEX IF NOT EXISTS quarantine_counters_tenant_idx
  ON quarantine_counters_minute (tenant_id, bucket_minute DESC);

CREATE TABLE IF NOT EXISTS app_settings (
  key        TEXT NOT NULL PRIMARY KEY,
  value      TEXT NOT NULL,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
