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

-- RLS: EXEMPT - schedule layer templates inherit tenant boundaries from schedule joins
CREATE TABLE IF NOT EXISTS oncall_layers (
    layer_id              SERIAL PRIMARY KEY,
    schedule_id           INTEGER NOT NULL REFERENCES oncall_schedules(schedule_id) ON DELETE CASCADE,
    name                  TEXT NOT NULL DEFAULT 'Layer 1',
    rotation_type         TEXT NOT NULL DEFAULT 'weekly',
    shift_duration_hours  INTEGER NOT NULL DEFAULT 168,
    handoff_day           INTEGER NOT NULL DEFAULT 1,
    handoff_hour          INTEGER NOT NULL DEFAULT 9,
    responders            JSONB NOT NULL DEFAULT '[]',
    layer_order           INTEGER NOT NULL DEFAULT 0,
    created_at            TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- RLS: EXEMPT - overrides inherit tenant boundaries from schedule joins
CREATE TABLE IF NOT EXISTS oncall_overrides (
    override_id      SERIAL PRIMARY KEY,
    schedule_id      INTEGER NOT NULL REFERENCES oncall_schedules(schedule_id) ON DELETE CASCADE,
    layer_id         INTEGER REFERENCES oncall_layers(layer_id) ON DELETE CASCADE,
    responder        TEXT NOT NULL,
    start_at         TIMESTAMPTZ NOT NULL,
    end_at           TIMESTAMPTZ NOT NULL,
    reason           TEXT,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CHECK (end_at > start_at)
);

ALTER TABLE escalation_levels
    ADD COLUMN IF NOT EXISTS oncall_schedule_id INTEGER
        REFERENCES oncall_schedules(schedule_id) ON DELETE SET NULL;

CREATE INDEX IF NOT EXISTS idx_oncall_schedules_tenant
    ON oncall_schedules (tenant_id);
CREATE INDEX IF NOT EXISTS idx_oncall_overrides_schedule_time
    ON oncall_overrides (schedule_id, start_at, end_at);
