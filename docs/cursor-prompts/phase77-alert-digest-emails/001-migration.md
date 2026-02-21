# Prompt 001 — Migration: alert_digest_settings

First check the highest migration number in `db/migrations/` (ls db/migrations/ | sort). Use the next number.

Create `db/migrations/0XX_alert_digest_settings.sql`:

```sql
CREATE TABLE IF NOT EXISTS alert_digest_settings (
    tenant_id       TEXT PRIMARY KEY,
    frequency       TEXT NOT NULL DEFAULT 'daily'
                    CHECK (frequency IN ('daily', 'weekly', 'disabled')),
    email           TEXT NOT NULL,
    last_sent_at    TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

No RLS needed — this table is queried by subscription_worker with superuser privileges.

## Acceptance Criteria
- [ ] Migration file exists with correct sequential number
- [ ] alert_digest_settings table with frequency check constraint
