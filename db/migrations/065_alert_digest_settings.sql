BEGIN;

CREATE TABLE IF NOT EXISTS alert_digest_settings (
    tenant_id       TEXT PRIMARY KEY,
    frequency       TEXT NOT NULL DEFAULT 'daily'
                    CHECK (frequency IN ('daily', 'weekly', 'disabled')),
    email           TEXT NOT NULL,
    last_sent_at    TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

COMMIT;
