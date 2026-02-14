BEGIN;

ALTER TABLE alert_rules
    DROP CONSTRAINT IF EXISTS chk_alert_rules_operator;

UPDATE alert_rules SET operator = 'GT' WHERE operator = '>';
UPDATE alert_rules SET operator = 'LT' WHERE operator = '<';
UPDATE alert_rules SET operator = 'GTE' WHERE operator = '>=';
UPDATE alert_rules SET operator = 'LTE' WHERE operator = '<=';

ALTER TABLE alert_rules
    ADD CONSTRAINT chk_alert_rules_operator
    CHECK (operator IN ('GT', 'LT', 'GTE', 'LTE'));

COMMIT;
