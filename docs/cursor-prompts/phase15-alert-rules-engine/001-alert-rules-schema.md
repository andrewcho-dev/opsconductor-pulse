# Task 001: Alert Rules Schema

> **CURSOR: EXECUTE THIS TASK**
>
> Read the instructions below and implement them exactly.
> Modify only the files listed in "Files to Modify".
> RUN THE TESTS in the Test section. Do not proceed if tests fail.
> IMPORTANT: Do not commit until all tests pass.

---

## Context

**THE PROBLEM**: The evaluator only generates `NO_HEARTBEAT` alerts. Customers cannot define threshold alerts like "alert when battery_pct < 20" or "alert when temp_c > 85". We need a database table to store customer-defined alert rules.

**Read first**:
- `services/evaluator_iot/evaluator.py` — focus on the DDL block (lines 20-56) and `ensure_schema()` (lines 61-65)

---

## Task

### 1.1 Add alert_rules table to evaluator DDL

**File**: `services/evaluator_iot/evaluator.py`

In the `DDL` string (after the `CREATE INDEX` statements around line 55), add the `alert_rules` table:

```sql
CREATE TABLE IF NOT EXISTS alert_rules (
  tenant_id       TEXT NOT NULL,
  rule_id         TEXT NOT NULL DEFAULT gen_random_uuid()::text,
  name            TEXT NOT NULL,
  enabled         BOOLEAN NOT NULL DEFAULT true,
  metric_name     TEXT NOT NULL,
  operator        TEXT NOT NULL,
  threshold       DOUBLE PRECISION NOT NULL,
  severity        INT NOT NULL DEFAULT 3,
  description     TEXT NULL,
  site_ids        TEXT[] NULL,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (tenant_id, rule_id)
);

CREATE INDEX IF NOT EXISTS alert_rules_tenant_idx ON alert_rules (tenant_id, enabled);
```

**Column definitions**:
- `tenant_id` — tenant scoping (multi-tenant isolation)
- `rule_id` — UUID as text, auto-generated
- `name` — human-readable rule name (e.g., "Low Battery Warning")
- `enabled` — toggle rule on/off without deleting
- `metric_name` — the metric key to evaluate (e.g., "battery_pct", "temp_c", "pressure_psi")
- `operator` — comparison operator: `GT` (>), `LT` (<), `GTE` (>=), `LTE` (<=)
- `threshold` — the numeric threshold value
- `severity` — alert severity 1-5 (1=INFO, 3=WARNING, 5=CRITICAL)
- `description` — optional human description
- `site_ids` — optional array to limit rule to specific sites (NULL means all sites)
- `created_at`, `updated_at` — timestamps

**Operator semantics**:
- `GT`: alert when `metric_value > threshold`
- `LT`: alert when `metric_value < threshold`
- `GTE`: alert when `metric_value >= threshold`
- `LTE`: alert when `metric_value <= threshold`

### 1.2 Verify ensure_schema handles the new DDL

The existing `ensure_schema()` function (line 61-65) splits the DDL on `;` and executes each statement. The new `CREATE TABLE IF NOT EXISTS` and `CREATE INDEX IF NOT EXISTS` are idempotent and will work with this pattern. No changes needed to `ensure_schema()` itself — just verify it still works.

---

## Files to Modify

| Action | Path | What changes |
|--------|------|--------------|
| MODIFY | `services/evaluator_iot/evaluator.py` | Add alert_rules CREATE TABLE and CREATE INDEX to DDL string |

---

## Test

### Step 1: Run existing unit tests

```bash
cd /home/opsconductor/simcloud && python3 -m pytest tests/unit/ -v -x
```

All existing tests must pass. The schema change is additive (CREATE IF NOT EXISTS) and cannot break anything.

### Step 2: Verify DDL

Read `services/evaluator_iot/evaluator.py` and confirm:
- [ ] `alert_rules` table definition exists in the DDL string
- [ ] Table has all columns: tenant_id, rule_id, name, enabled, metric_name, operator, threshold, severity, description, site_ids, created_at, updated_at
- [ ] Primary key is `(tenant_id, rule_id)`
- [ ] Index exists on `(tenant_id, enabled)`
- [ ] `rule_id` defaults to `gen_random_uuid()::text`

---

## Acceptance Criteria

- [ ] `alert_rules` table DDL added to evaluator.py DDL string
- [ ] Table uses `CREATE TABLE IF NOT EXISTS` (idempotent)
- [ ] Index uses `CREATE INDEX IF NOT EXISTS` (idempotent)
- [ ] All existing unit tests pass

---

## Commit

```
Add alert_rules table schema for custom threshold alerts

Create alert_rules table for customer-defined threshold rules.
Supports metric_name, operator (GT/LT/GTE/LTE), threshold,
severity, and optional site_ids filter.

Phase 15 Task 1: Alert Rules Schema
```
