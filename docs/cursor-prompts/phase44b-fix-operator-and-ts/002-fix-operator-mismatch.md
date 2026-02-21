# Prompt 002 — Fix Operator Mismatch

## Context

Based on the diagnosis in prompt 001, there is a mismatch between what the API accepts (`GT`, `LT`, `GTE`, `LTE`) and what the DB constraint allows (`>`, `<`, `>=`, `<=`).

The evaluator's `OPERATOR_SYMBOLS` dict already translates named → symbol form for display. The evaluator's `evaluate_threshold()` uses the named form (`GT`, `LT`, etc.).

## Decision

**The named form (`GT`, `LT`, `GTE`, `LTE`) is the canonical representation.** It is what the evaluator uses, what the API validates, and what should be stored in the DB. The DB constraint must be updated to accept the named form.

Do NOT change the evaluator or the API validation. Fix the DB constraint to match.

## Your Task

### Step 1: Write migration `db/migrations/055_fix_operator_constraint.sql`

```sql
BEGIN;

ALTER TABLE alert_rules
    DROP CONSTRAINT IF EXISTS chk_alert_rules_operator;

ALTER TABLE alert_rules
    ADD CONSTRAINT chk_alert_rules_operator
    CHECK (operator IN ('GT', 'LT', 'GTE', 'LTE', 'EQ', 'NEQ'));

COMMIT;
```

Note: Include `EQ` and `NEQ` if the evaluator's `OPERATOR_SYMBOLS` dict includes `==` and `!=` equivalents. Check `evaluator.py` — if those operators exist in the code, add them. If not, omit them.

### Step 2: Check for existing rows with symbol-form operators

```bash
docker compose exec db psql -U iot -d iotcloud -c \
  "SELECT COUNT(*) FROM alert_rules WHERE operator IN ('>', '<', '>=', '<=', '==', '!=');"
```

If any rows exist with the old symbol form, write a data migration in the same SQL file to convert them before adding the new constraint:

```sql
UPDATE alert_rules SET operator = 'GT' WHERE operator = '>';
UPDATE alert_rules SET operator = 'LT' WHERE operator = '<';
UPDATE alert_rules SET operator = 'GTE' WHERE operator = '>=';
UPDATE alert_rules SET operator = 'LTE' WHERE operator = '<=';
```

Place the UPDATEs BEFORE the DROP/ADD CONSTRAINT in the migration.

### Step 3: Apply the migration

```bash
docker compose exec db psql -U iot -d iotcloud -f /migrations/055_fix_operator_constraint.sql
```

### Step 4: Re-test the POST

```bash
curl -s -X POST http://localhost/api/customer/alert-rules \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Sustained High Temp Test",
    "metric_name": "temp_c",
    "operator": "GT",
    "threshold": 40,
    "severity": 3,
    "duration_seconds": 60
  }' | jq .
```

Expected: 201 Created with `duration_seconds: 60` in response.

## Acceptance Criteria

- [ ] Migration `055_fix_operator_constraint.sql` exists and applied
- [ ] DB constraint now accepts `GT`, `LT`, `GTE`, `LTE`
- [ ] Any existing symbol-form rows converted to named form
- [ ] `POST /customer/alert-rules` with `operator: "GT"` returns 201
- [ ] `pytest -m unit -v` passes (FakeConn tests are unaffected by DB constraint)
