# Prompt 001 — Migration: device_groups + device_group_members

Create `db/migrations/061_device_groups.sql`:

```sql
BEGIN;

CREATE TABLE IF NOT EXISTS device_groups (
    group_id     TEXT        NOT NULL,
    tenant_id    TEXT        NOT NULL REFERENCES tenants(tenant_id) ON DELETE CASCADE,
    name         TEXT        NOT NULL,
    description  TEXT        NULL,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (tenant_id, group_id)
);

CREATE TABLE IF NOT EXISTS device_group_members (
    tenant_id    TEXT  NOT NULL,
    group_id     TEXT  NOT NULL,
    device_id    TEXT  NOT NULL,
    added_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (tenant_id, group_id, device_id),
    FOREIGN KEY (tenant_id, group_id) REFERENCES device_groups(tenant_id, group_id) ON DELETE CASCADE
);

-- Add group_ids to alert_rules for group-scoped rules
ALTER TABLE alert_rules
    ADD COLUMN IF NOT EXISTS group_ids TEXT[] NULL;

COMMENT ON COLUMN alert_rules.group_ids IS
    'If set, rule only evaluates devices belonging to one of these group_ids.';

-- Indexes
CREATE INDEX IF NOT EXISTS idx_device_groups_tenant
    ON device_groups(tenant_id);

CREATE INDEX IF NOT EXISTS idx_device_group_members_device
    ON device_group_members(tenant_id, device_id);

ENABLE ROW LEVEL SECURITY ON device_groups;
ENABLE ROW LEVEL SECURITY ON device_group_members;

CREATE POLICY device_groups_tenant_isolation ON device_groups
    USING (tenant_id = current_setting('app.tenant_id', true));

CREATE POLICY device_group_members_tenant_isolation ON device_group_members
    USING (tenant_id = current_setting('app.tenant_id', true));

COMMIT;
```

## Acceptance Criteria

- [ ] `061_device_groups.sql` exists
- [ ] `device_groups` table created with RLS
- [ ] `device_group_members` junction table created with RLS
- [ ] `group_ids TEXT[]` added to `alert_rules`
- [ ] `pytest -m unit -v` passes
