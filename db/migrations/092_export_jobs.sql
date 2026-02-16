-- Migration 092: Async data export infrastructure
-- Phase 129 - Async data export jobs with background processing
-- Date: 2026-02-16

BEGIN;

-- Export job lifecycle:
--   PENDING -> PROCESSING -> COMPLETED / FAILED
CREATE TABLE IF NOT EXISTS export_jobs (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id       TEXT NOT NULL REFERENCES tenants(tenant_id),
    export_type     TEXT NOT NULL CHECK (export_type IN ('devices', 'alerts', 'telemetry')),
    format          TEXT NOT NULL DEFAULT 'csv' CHECK (format IN ('json', 'csv')),
    filters         JSONB NOT NULL DEFAULT '{}',
    status          TEXT NOT NULL DEFAULT 'PENDING'
                        CHECK (status IN ('PENDING', 'PROCESSING', 'COMPLETED', 'FAILED')),
    file_path       TEXT,
    file_size_bytes BIGINT,
    row_count       INTEGER,
    error           TEXT,
    callback_url    TEXT,
    created_by      TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    started_at      TIMESTAMPTZ,
    completed_at    TIMESTAMPTZ,
    expires_at      TIMESTAMPTZ DEFAULT NOW() + INTERVAL '24 hours'
);

-- Index for the worker to find pending jobs efficiently
CREATE INDEX IF NOT EXISTS idx_export_jobs_status
    ON export_jobs (status, created_at)
    WHERE status = 'PENDING';

-- Index for tenant queries
CREATE INDEX IF NOT EXISTS idx_export_jobs_tenant
    ON export_jobs (tenant_id, created_at DESC);

-- Enable RLS (tenant-scoped access via app.tenant_id)
ALTER TABLE export_jobs ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS export_jobs_tenant_isolation ON export_jobs;
CREATE POLICY export_jobs_tenant_isolation ON export_jobs
    USING (tenant_id = current_setting('app.tenant_id', true))
    WITH CHECK (tenant_id = current_setting('app.tenant_id', true));

-- GRANTS
GRANT SELECT, INSERT, UPDATE, DELETE ON export_jobs TO pulse_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON export_jobs TO pulse_operator;

COMMIT;

