-- Migration 077: IoT Jobs
-- Modelled on AWS IoT Jobs. Two tables:
--   jobs            - one row per job created by an operator
--   job_executions  - one row per (job, device) - tracks per-device progress

-- ----------------------------------------------------------------
-- 1. jobs
-- ----------------------------------------------------------------
CREATE TABLE IF NOT EXISTS jobs (
    job_id          TEXT        NOT NULL,
    tenant_id       TEXT        NOT NULL REFERENCES tenants(tenant_id) ON DELETE CASCADE,

    -- Document
    document_type   TEXT        NOT NULL,
    document_params JSONB       NOT NULL DEFAULT '{}',

    -- Target (one of these is set)
    target_device_id  TEXT,
    target_group_id   TEXT,
    target_all        BOOLEAN   NOT NULL DEFAULT FALSE,

    -- Lifecycle
    status          TEXT        NOT NULL DEFAULT 'IN_PROGRESS'
                    CHECK (status IN ('IN_PROGRESS','COMPLETED','CANCELED','DELETION_IN_PROGRESS')),

    -- TTL
    expires_at      TIMESTAMPTZ,

    -- Audit
    created_by      TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    PRIMARY KEY (tenant_id, job_id),

    -- Exactly one target must be set
    CONSTRAINT jobs_target_check CHECK (
        (target_device_id IS NOT NULL)::INT +
        (target_group_id  IS NOT NULL)::INT +
        (target_all = TRUE)::INT = 1
    )
);

CREATE INDEX IF NOT EXISTS idx_jobs_tenant_status
    ON jobs (tenant_id, status);

CREATE INDEX IF NOT EXISTS idx_jobs_expires_at
    ON jobs (expires_at)
    WHERE expires_at IS NOT NULL AND status = 'IN_PROGRESS';

ALTER TABLE jobs ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS jobs_tenant_isolation ON jobs;
CREATE POLICY jobs_tenant_isolation ON jobs
    USING (tenant_id = current_setting('app.tenant_id', true))
    WITH CHECK (tenant_id = current_setting('app.tenant_id', true));

-- ----------------------------------------------------------------
-- 2. job_executions
-- ----------------------------------------------------------------
CREATE TABLE IF NOT EXISTS job_executions (
    job_id          TEXT        NOT NULL,
    tenant_id       TEXT        NOT NULL,
    device_id       TEXT        NOT NULL,

    -- Lifecycle
    status          TEXT        NOT NULL DEFAULT 'QUEUED'
                    CHECK (status IN (
                        'QUEUED','IN_PROGRESS','SUCCEEDED',
                        'FAILED','TIMED_OUT','REJECTED'
                    )),

    -- Device-reported outcome
    status_details  JSONB,

    -- Execution version
    execution_number BIGINT     NOT NULL DEFAULT 1,

    -- Timestamps
    queued_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    started_at      TIMESTAMPTZ,
    last_updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    PRIMARY KEY (tenant_id, job_id, device_id),
    FOREIGN KEY (tenant_id, job_id) REFERENCES jobs (tenant_id, job_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_job_executions_device_queued
    ON job_executions (tenant_id, device_id, status)
    WHERE status IN ('QUEUED', 'IN_PROGRESS');

CREATE INDEX IF NOT EXISTS idx_job_executions_job_id
    ON job_executions (tenant_id, job_id);

ALTER TABLE job_executions ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS job_executions_tenant_isolation ON job_executions;
CREATE POLICY job_executions_tenant_isolation ON job_executions
    USING (tenant_id = current_setting('app.tenant_id', true))
    WITH CHECK (tenant_id = current_setting('app.tenant_id', true));

-- ----------------------------------------------------------------
-- Verify
-- ----------------------------------------------------------------
SELECT table_name FROM information_schema.tables
WHERE table_name IN ('jobs', 'job_executions')
ORDER BY table_name;
