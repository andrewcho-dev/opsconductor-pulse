-- Migration 074: Add duration_minutes to alert_rules
-- NULL = instant fire (existing behaviour preserved)
-- integer > 0 = condition must hold for N continuous minutes

ALTER TABLE alert_rules
  ADD COLUMN IF NOT EXISTS duration_minutes INTEGER DEFAULT NULL
    CHECK (duration_minutes IS NULL OR duration_minutes > 0);

-- Backfill from duration_seconds when already configured in minute units.
UPDATE alert_rules
SET duration_minutes = duration_seconds / 60
WHERE duration_minutes IS NULL
  AND duration_seconds IS NOT NULL
  AND duration_seconds > 0
  AND duration_seconds % 60 = 0;

COMMENT ON COLUMN alert_rules.duration_minutes IS
  'If set, alert fires only when condition holds for this many consecutive minutes. NULL = fire on first sample.';

-- Verify
SELECT column_name, data_type, column_default, is_nullable
FROM information_schema.columns
WHERE table_name = 'alert_rules' AND column_name = 'duration_minutes';
