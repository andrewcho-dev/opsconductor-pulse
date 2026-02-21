# Phase 90 — Migration: report_runs

## File
`db/migrations/067_report_runs.sql`

## SQL

```sql
-- Migration 067: report run history
CREATE TABLE IF NOT EXISTS report_runs (
    run_id          SERIAL PRIMARY KEY,
    tenant_id       TEXT NOT NULL,
    report_type     TEXT NOT NULL,
        -- 'sla_summary' | 'device_export' | 'alert_export'
    status          TEXT NOT NULL DEFAULT 'pending',
        -- 'pending' | 'running' | 'done' | 'failed'
    triggered_by    TEXT,
        -- 'scheduled' | 'user:{user_id}'
    parameters      JSONB NOT NULL DEFAULT '{}',
    row_count       INTEGER,
    error_message   TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at    TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_report_runs_tenant
    ON report_runs (tenant_id, created_at DESC);
```

## Apply
```bash
psql "$DATABASE_URL" -f db/migrations/067_report_runs.sql
```
