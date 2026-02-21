# Prompt 001 — Migration: alert_maintenance_windows

Create `db/migrations/062_maintenance_windows.sql`:

```sql
BEGIN;

CREATE TABLE IF NOT EXISTS alert_maintenance_windows (
    window_id    TEXT        NOT NULL DEFAULT gen_random_uuid()::text,
    tenant_id    TEXT        NOT NULL REFERENCES tenants(tenant_id) ON DELETE CASCADE,
    name         TEXT        NOT NULL,
    starts_at    TIMESTAMPTZ NOT NULL,
    ends_at      TIMESTAMPTZ NULL,        -- NULL = indefinite
    recurring    JSONB       NULL,        -- {dow:[0-6], start_hour:2, end_hour:4}
    site_ids     TEXT[]      NULL,        -- NULL = all sites
    device_types TEXT[]      NULL,        -- NULL = all device types
    enabled      BOOLEAN     NOT NULL DEFAULT true,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (tenant_id, window_id)
);

COMMENT ON COLUMN alert_maintenance_windows.recurring IS
    'If set, window recurs weekly. Format: {"dow":[0,6],"start_hour":2,"end_hour":4} (0=Sunday).';

COMMENT ON COLUMN alert_maintenance_windows.ends_at IS
    'NULL means the window is indefinite (disabled manually or via enabled=false).';

-- Index for evaluator: find active windows per tenant
CREATE INDEX IF NOT EXISTS idx_maint_windows_active
    ON alert_maintenance_windows(tenant_id, starts_at, ends_at)
    WHERE enabled = true;

ENABLE ROW LEVEL SECURITY ON alert_maintenance_windows;

CREATE POLICY maint_windows_tenant_isolation ON alert_maintenance_windows
    USING (tenant_id = current_setting('app.tenant_id', true));

COMMIT;
```

## Acceptance Criteria

- [ ] `062_maintenance_windows.sql` exists
- [ ] `alert_maintenance_windows` table created with RLS
- [ ] `idx_maint_windows_active` index created
- [ ] `pytest -m unit -v` passes
