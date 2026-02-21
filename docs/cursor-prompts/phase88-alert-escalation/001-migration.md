# Phase 88 — Migration: escalation_policies

## File
`db/migrations/066_escalation_policies.sql`

## SQL

```sql
-- Migration 066: escalation policies
CREATE TABLE IF NOT EXISTS escalation_policies (
    policy_id       SERIAL PRIMARY KEY,
    tenant_id       TEXT NOT NULL,
    name            TEXT NOT NULL,
    description     TEXT,
    is_default      BOOLEAN NOT NULL DEFAULT FALSE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS escalation_levels (
    level_id        SERIAL PRIMARY KEY,
    policy_id       INTEGER NOT NULL REFERENCES escalation_policies(policy_id) ON DELETE CASCADE,
    level_number    INTEGER NOT NULL CHECK (level_number BETWEEN 1 AND 5),
    delay_minutes   INTEGER NOT NULL DEFAULT 15,
    notify_email    TEXT,
    notify_webhook  TEXT,
    UNIQUE (policy_id, level_number)
);

-- Link alert rules to a policy
ALTER TABLE alert_rules
    ADD COLUMN IF NOT EXISTS escalation_policy_id INTEGER
        REFERENCES escalation_policies(policy_id) ON DELETE SET NULL;

-- Track escalation state on open alerts
ALTER TABLE alerts
    ADD COLUMN IF NOT EXISTS escalation_level   INTEGER NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS next_escalation_at TIMESTAMPTZ;

CREATE INDEX IF NOT EXISTS idx_alerts_next_escalation
    ON alerts (next_escalation_at)
    WHERE status = 'OPEN' AND next_escalation_at IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_escalation_policies_tenant
    ON escalation_policies (tenant_id);
```

## Apply
```bash
psql "$DATABASE_URL" -f db/migrations/066_escalation_policies.sql
```
