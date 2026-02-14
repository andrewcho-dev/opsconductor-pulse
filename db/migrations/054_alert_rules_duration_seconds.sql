BEGIN;

ALTER TABLE alert_rules
    ADD COLUMN IF NOT EXISTS duration_seconds INTEGER NOT NULL DEFAULT 0;

COMMENT ON COLUMN alert_rules.duration_seconds IS
    'Minimum seconds the threshold must be continuously breached before an alert fires. 0 = fire immediately (default, backwards compatible).';

COMMIT;
