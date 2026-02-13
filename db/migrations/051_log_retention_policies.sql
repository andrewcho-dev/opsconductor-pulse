-- ============================================
-- Migration: 051_log_retention_policies.sql
-- Purpose: Maintenance tracking and optional retention tightening
-- Note: telemetry (30d), system_metrics (7d), audit_log (90d) already
--       have retention in 023 and 028.
-- ============================================

BEGIN;

-- ============================================
-- 1. Optional: tighten audit_log to 7 days
--    (Uncomment if you need to reduce audit volume)
-- ============================================
-- SELECT remove_retention_policy('audit_log');
-- SELECT add_retention_policy('audit_log', INTERVAL '7 days', if_not_exists => TRUE);

-- ============================================
-- 2. Maintenance log (track cleanup runs)
-- ============================================

CREATE TABLE IF NOT EXISTS maintenance_log (
    id BIGSERIAL PRIMARY KEY,
    job_name TEXT NOT NULL,
    started_at TIMESTAMPTZ NOT NULL,
    completed_at TIMESTAMPTZ,
    rows_affected BIGINT,
    status TEXT NOT NULL DEFAULT 'RUNNING',
    error_message TEXT,
    details JSONB
);

CREATE INDEX IF NOT EXISTS idx_maintenance_log_job
    ON maintenance_log(job_name, started_at DESC);

COMMENT ON TABLE maintenance_log IS 'Tracks scheduled maintenance jobs (e.g. log cleanup)';

COMMIT;
