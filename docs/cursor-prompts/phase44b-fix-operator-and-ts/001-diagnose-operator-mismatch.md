# Prompt 001 — Diagnose Operator Mismatch (Read Only)

## Your Task

Read and report the exact state of the operator representation across every layer. Do NOT change anything yet.

### Step 1: Read the DB constraint

Find the migration that creates `chk_alert_rules_operator`. It will be in `db/migrations/`. Search for `chk_alert_rules_operator` or `CHECK.*operator`. Report the exact constraint definition.

```bash
grep -r "chk_alert_rules_operator\|operator.*CHECK\|CHECK.*operator" db/migrations/ --include="*.sql" -l
```

Then read the relevant migration file. Report exactly what values the constraint allows.

### Step 2: Read the API validation

In `services/ui_iot/routes/customer.py`, find `VALID_OPERATORS`. Report its exact value.

### Step 3: Read what the evaluator stores / queries

In `services/evaluator_iot/evaluator.py`, find:
- `OPERATOR_SYMBOLS` dict — maps named form to symbol
- `fetch_tenant_rules()` — reports what format is stored in DB (whatever the SELECT returns is what's in the DB)
- `evaluate_threshold()` — what format does it expect? (`GT`/`LT` or `>`/`<`?)

### Step 4: Check existing DB data

```bash
docker compose exec db psql -U iot -d iotcloud -c "SELECT DISTINCT operator FROM alert_rules;"
```

Report what values are actually stored.

### Step 5: Write a diagnosis

After reading all the above, answer:
- What format does the DB constraint enforce?
- What format does the API accept from customers?
- What format does the evaluator expect?
- What format is currently stored in the DB?
- Where is the translation happening (if anywhere)?

Write these findings as a comment block at the top of `services/ui_iot/routes/customer.py`:

```python
# PHASE 44b DIAGNOSIS — Operator Format:
# DB constraint allows: [exact values from migration]
# API VALID_OPERATORS: [current value]
# Evaluator expects: [GT/LT or >/< ?]
# Currently stored in DB: [from SELECT DISTINCT]
# Translation layer: [where/if it happens]
# Decision: [see prompt 002]
```

## Acceptance Criteria

- [ ] Diagnosis comment added to customer.py
- [ ] All 5 questions answered
- [ ] No code changed
