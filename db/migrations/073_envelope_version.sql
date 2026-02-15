-- Migration 073: Track envelope version in quarantine for diagnostics
-- The telemetry table does not need envelope_version (hot path, avoid schema churn).
-- quarantine_events benefits from it for debugging unknown-version rejections.

ALTER TABLE quarantine_events
  ADD COLUMN IF NOT EXISTS envelope_version TEXT DEFAULT '1';

-- Update existing rows to have explicit version
UPDATE quarantine_events SET envelope_version = '1' WHERE envelope_version IS NULL;

-- Verify
SELECT column_name, data_type, column_default
FROM information_schema.columns
WHERE table_name = 'quarantine_events' AND column_name = 'envelope_version';
