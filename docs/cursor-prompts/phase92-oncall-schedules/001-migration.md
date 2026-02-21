# Phase 92 — Migration: On-Call Schedules

## File
`db/migrations/069_oncall_schedules.sql`

## SQL

```sql
-- Migration 069: on-call schedules

CREATE TABLE IF NOT EXISTS oncall_schedules (
    schedule_id     SERIAL PRIMARY KEY,
    tenant_id       TEXT NOT NULL,
    name            TEXT NOT NULL,
    description     TEXT,
    timezone        TEXT NOT NULL DEFAULT 'UTC',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- A layer is one rotation within a schedule (e.g. "Primary On-Call")
CREATE TABLE IF NOT EXISTS oncall_layers (
    layer_id        SERIAL PRIMARY KEY,
    schedule_id     INTEGER NOT NULL REFERENCES oncall_schedules(schedule_id) ON DELETE CASCADE,
    name            TEXT NOT NULL DEFAULT 'Layer 1',
    rotation_type   TEXT NOT NULL DEFAULT 'weekly',
        -- 'daily' | 'weekly' | 'custom'
    shift_duration_hours INTEGER NOT NULL DEFAULT 168,  -- 168 = 1 week
    handoff_day     INTEGER NOT NULL DEFAULT 1,   -- 0=Sun, 1=Mon ... 6=Sat
    handoff_hour    INTEGER NOT NULL DEFAULT 9,   -- local hour in schedule timezone
    -- Ordered list of responders (user names or email addresses)
    -- Stored as JSONB array: ["alice@co.com", "bob@co.com", "carol@co.com"]
    responders      JSONB NOT NULL DEFAULT '[]',
    layer_order     INTEGER NOT NULL DEFAULT 0,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Temporary overrides (e.g. vacation cover)
CREATE TABLE IF NOT EXISTS oncall_overrides (
    override_id     SERIAL PRIMARY KEY,
    schedule_id     INTEGER NOT NULL REFERENCES oncall_schedules(schedule_id) ON DELETE CASCADE,
    layer_id        INTEGER REFERENCES oncall_layers(layer_id) ON DELETE CASCADE,
    responder       TEXT NOT NULL,   -- who is on-call during this override
    start_at        TIMESTAMPTZ NOT NULL,
    end_at          TIMESTAMPTZ NOT NULL,
    reason          TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CHECK (end_at > start_at)
);

-- Link escalation levels to a schedule
ALTER TABLE escalation_levels
    ADD COLUMN IF NOT EXISTS oncall_schedule_id INTEGER
        REFERENCES oncall_schedules(schedule_id) ON DELETE SET NULL;

CREATE INDEX IF NOT EXISTS idx_oncall_schedules_tenant
    ON oncall_schedules (tenant_id);
CREATE INDEX IF NOT EXISTS idx_oncall_overrides_schedule_time
    ON oncall_overrides (schedule_id, start_at, end_at);
```

## Apply
```bash
psql "$DATABASE_URL" -f db/migrations/069_oncall_schedules.sql
```
