-- Ensure required columns exist
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'alert_rules' AND column_name = 'metric_name'
    ) THEN
        ALTER TABLE alert_rules ADD COLUMN metric_name TEXT;
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'alert_rules' AND column_name = 'operator'
    ) THEN
        ALTER TABLE alert_rules ADD COLUMN operator TEXT;
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'alert_rules' AND column_name = 'threshold'
    ) THEN
        ALTER TABLE alert_rules ADD COLUMN threshold NUMERIC;
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'alert_rules' AND column_name = 'severity'
    ) THEN
        ALTER TABLE alert_rules ADD COLUMN severity TEXT DEFAULT 'medium';
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'alert_rules' AND column_name = 'site_ids'
    ) THEN
        ALTER TABLE alert_rules ADD COLUMN site_ids TEXT[];
    END IF;
END $$;

-- Normalize operator values to allowed set
UPDATE alert_rules SET operator = '>' WHERE operator IN ('gt', 'greater', 'greater_than', 'GT');
UPDATE alert_rules SET operator = '<' WHERE operator IN ('lt', 'less', 'less_than', 'LT');
UPDATE alert_rules SET operator = '>=' WHERE operator IN ('gte', 'ge', 'greater_equal', 'GTE');
UPDATE alert_rules SET operator = '<=' WHERE operator IN ('lte', 'le', 'less_equal', 'LTE');
UPDATE alert_rules SET operator = '==' WHERE operator IN ('eq', 'equal', 'equals', 'EQ', '=');
UPDATE alert_rules SET operator = '!=' WHERE operator IN ('ne', 'neq', 'not_equal', 'NE', '<>');

UPDATE alert_rules
SET operator = '>'
WHERE operator NOT IN ('>', '<', '>=', '<=', '==', '!=');

-- Add constraints if missing
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'chk_alert_rules_operator'
    ) THEN
        ALTER TABLE alert_rules
        DROP CONSTRAINT IF EXISTS chk_alert_rules_operator;
        ALTER TABLE alert_rules
        ADD CONSTRAINT chk_alert_rules_operator
        CHECK (operator IN ('>', '<', '>=', '<=', '==', '!='));
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'chk_alert_rules_severity'
    ) AND EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'alert_rules'
          AND column_name = 'severity'
          AND data_type = 'text'
    ) THEN
        ALTER TABLE alert_rules
        ADD CONSTRAINT chk_alert_rules_severity
        CHECK (severity IN ('critical', 'high', 'medium', 'low', 'info'));
    END IF;
END $$;
