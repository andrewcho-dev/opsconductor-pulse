BEGIN;

-- Add aggregation function column: avg, min, max, count, sum
ALTER TABLE alert_rules
    ADD COLUMN IF NOT EXISTS aggregation VARCHAR(10) NULL;

-- Add sliding window duration in seconds
ALTER TABLE alert_rules
    ADD COLUMN IF NOT EXISTS window_seconds INTEGER NULL;

-- Validate aggregation values
ALTER TABLE alert_rules
    ADD CONSTRAINT chk_aggregation_values
    CHECK (aggregation IS NULL OR aggregation IN ('avg', 'min', 'max', 'count', 'sum'));

-- Validate window_seconds range: 60s to 3600s (1 min to 1 hour)
ALTER TABLE alert_rules
    ADD CONSTRAINT chk_window_seconds_range
    CHECK (window_seconds IS NULL OR (window_seconds >= 60 AND window_seconds <= 3600));

-- If rule_type is WINDOW, aggregation and window_seconds must both be set
-- (enforced at application level, not DB constraint, to avoid migration pain)

COMMENT ON COLUMN alert_rules.aggregation IS 'Aggregation function for WINDOW rules: avg, min, max, count, sum';
COMMENT ON COLUMN alert_rules.window_seconds IS 'Sliding window duration in seconds for WINDOW rules (60-3600)';

COMMIT;

