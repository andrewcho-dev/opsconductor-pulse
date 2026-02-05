# Task 005: Tests and Documentation

> **CURSOR: EXECUTE THIS TASK**
>
> Read the instructions below and implement them exactly.
> Modify only the files listed in "Files to Modify".
> RUN THE TESTS in the Test section. Do not proceed if tests fail.
> IMPORTANT: Do not commit until all tests pass.

---

## Context

Phase 15 Tasks 001-004 added: alert rules schema, CRUD API, customer UI, and rule evaluation engine. This task adds unit tests for the evaluation logic, CRUD validation, and updates documentation.

**Read first**:
- `services/evaluator_iot/evaluator.py` — the `evaluate_threshold` function and `OPERATOR_SYMBOLS` constant
- `services/ui_iot/routes/customer.py` — the `VALID_OPERATORS`, `AlertRuleCreate`, `AlertRuleUpdate` models
- `tests/unit/test_dispatcher_logic.py` — existing test pattern for dispatcher (mock-based, no DB)
- `tests/unit/test_ingest_pipeline.py` — existing test pattern for module imports with stubs

---

## Task

### 5.1 Create unit tests for evaluate_threshold

**File**: `tests/unit/test_alert_rules.py` (NEW)

Create a new test file. Import `evaluate_threshold` from the evaluator module. The evaluator imports `asyncpg` and `httpx` which may not be available in the test environment. Use the same stub pattern as other tests — or since `evaluate_threshold` is a pure function, you may be able to import it directly if the module-level imports don't fail. If they do, stub them:

```python
import sys
import types
import os
import pytest

# Stub modules not available in test environment
for mod in ["asyncpg", "httpx"]:
    if mod not in sys.modules:
        sys.modules[mod] = types.SimpleNamespace(
            AsyncClient=lambda **kw: None,
            create_pool=lambda **kw: None,
            Connection=type("Connection", (), {}),
            Pool=type("Pool", (), {}),
        )
if "dateutil" not in sys.modules:
    parser_stub = types.SimpleNamespace(isoparse=lambda _v: None)
    sys.modules["dateutil"] = types.SimpleNamespace(parser=parser_stub)
    sys.modules["dateutil.parser"] = parser_stub

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "services", "evaluator_iot"))
from evaluator import evaluate_threshold, OPERATOR_SYMBOLS
```

**Test cases** (all marked `@pytest.mark.unit`):

**evaluate_threshold — GT operator:**
- `test_gt_true`: `evaluate_threshold(25.0, "GT", 20.0)` → `True`
- `test_gt_false`: `evaluate_threshold(15.0, "GT", 20.0)` → `False`
- `test_gt_equal_is_false`: `evaluate_threshold(20.0, "GT", 20.0)` → `False`

**evaluate_threshold — LT operator:**
- `test_lt_true`: `evaluate_threshold(15.0, "LT", 20.0)` → `True`
- `test_lt_false`: `evaluate_threshold(25.0, "LT", 20.0)` → `False`
- `test_lt_equal_is_false`: `evaluate_threshold(20.0, "LT", 20.0)` → `False`

**evaluate_threshold — GTE operator:**
- `test_gte_greater`: `evaluate_threshold(25.0, "GTE", 20.0)` → `True`
- `test_gte_equal`: `evaluate_threshold(20.0, "GTE", 20.0)` → `True`
- `test_gte_less`: `evaluate_threshold(15.0, "GTE", 20.0)` → `False`

**evaluate_threshold — LTE operator:**
- `test_lte_less`: `evaluate_threshold(15.0, "LTE", 20.0)` → `True`
- `test_lte_equal`: `evaluate_threshold(20.0, "LTE", 20.0)` → `True`
- `test_lte_greater`: `evaluate_threshold(25.0, "LTE", 20.0)` → `False`

**evaluate_threshold — Edge cases:**
- `test_none_value`: `evaluate_threshold(None, "GT", 20.0)` → `False`
- `test_string_numeric`: `evaluate_threshold("25.5", "GT", 20.0)` → `True` (string cast to float)
- `test_string_non_numeric`: `evaluate_threshold("abc", "GT", 20.0)` → `False`
- `test_boolean_value`: `evaluate_threshold(True, "GT", 0.5)` → `True` (True → 1.0)
- `test_zero_threshold`: `evaluate_threshold(0.0, "LT", 0.0)` → `False` (0.0 is NOT < 0.0)
- `test_negative_values`: `evaluate_threshold(-95, "LT", -80)` → `True` (-95 < -80)
- `test_unknown_operator`: `evaluate_threshold(25.0, "INVALID", 20.0)` → `False`
- `test_integer_value`: `evaluate_threshold(25, "GT", 20.0)` → `True` (int works)

**OPERATOR_SYMBOLS:**
- `test_operator_symbols`: Verify `OPERATOR_SYMBOLS` has keys GT, LT, GTE, LTE with correct symbols

### 5.2 Test the Pydantic validation models

**File**: `tests/unit/test_alert_rules.py` (same file)

Test the Pydantic models from customer.py. Import them:

```python
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "services", "ui_iot"))
```

Note: This import may be complex due to FastAPI dependencies. If importing `AlertRuleCreate` directly is too difficult due to module dependencies, skip these tests and focus on the evaluator tests. The Pydantic validation is already tested implicitly by the API endpoints.

If the import works, test:
- `test_valid_rule_create`: Valid AlertRuleCreate with all fields
- `test_rule_create_invalid_severity`: Severity > 5 raises ValidationError
- `test_rule_create_missing_name`: Missing name raises ValidationError

### 5.3 Update Phase 15 documentation

**File**: `docs/cursor-prompts/README.md`

Add a Phase 15 section BEFORE the "How to Use These Prompts" section. Follow the same format as Phase 14:

```markdown
## Phase 15: Custom Alert Rules Engine

**Goal**: Customer-defined threshold alert rules evaluated against any device metric.

**Directory**: `phase15-alert-rules-engine/`

**Status**: COMPLETE

| # | File | Description | Status | Dependencies |
|---|------|-------------|--------|--------------|
| 1 | `001-alert-rules-schema.md` | alert_rules table in evaluator DDL | `[x]` | None |
| 2 | `002-alert-rules-crud-api.md` | CRUD API + database query functions | `[x]` | #1 |
| 3 | `003-alert-rules-ui.md` | Customer UI page with modal form | `[x]` | #2 |
| 4 | `004-rule-evaluation-engine.md` | Evaluator loads and evaluates rules | `[x]` | #1 |
| 5 | `005-tests-and-documentation.md` | Unit tests and documentation | `[x]` | #1-#4 |

**Exit Criteria**:
- [x] alert_rules table stores customer-defined threshold rules
- [x] CRUD API for alert rules (create, read, update, delete)
- [x] Customer UI page for managing alert rules
- [x] Evaluator evaluates threshold rules against device metrics
- [x] THRESHOLD alerts generated and auto-closed through existing fleet_alert lifecycle
- [x] Alerts flow through existing dispatcher → delivery pipeline
- [x] Unit tests for evaluate_threshold function
- [x] Nav link added to customer sidebar

**Alert rule types supported**:
- `GT`: metric > threshold (e.g., temp_c > 85)
- `LT`: metric < threshold (e.g., battery_pct < 20)
- `GTE`: metric >= threshold
- `LTE`: metric <= threshold

**Architecture note**: Rules are stored in PostgreSQL and loaded per-tenant per evaluator cycle. Generated THRESHOLD alerts use the same fleet_alert table, dispatcher routing, and delivery pipeline as NO_HEARTBEAT alerts. No changes needed to dispatcher or delivery_worker.
```

---

## Files to Modify

| Action | Path | What changes |
|--------|------|--------------|
| CREATE | `tests/unit/test_alert_rules.py` | Unit tests for evaluate_threshold and OPERATOR_SYMBOLS |
| MODIFY | `docs/cursor-prompts/README.md` | Add Phase 15 section |

---

## Test

### Step 1: Run ALL unit tests

```bash
cd /home/opsconductor/simcloud && python3 -m pytest tests/unit/ -v -x
```

ALL tests must pass, including the new test_alert_rules.py tests AND all existing tests.

### Step 2: Verify test counts

The new test file should have:
- 18+ evaluate_threshold tests (4 operators x 3 cases + edge cases)
- 1 OPERATOR_SYMBOLS test
- Total: 19+ new tests

---

## Acceptance Criteria

- [ ] test_alert_rules.py has 19+ tests for evaluate_threshold
- [ ] Tests cover all 4 operators (GT, LT, GTE, LTE)
- [ ] Tests cover edge cases (None, string, boolean, negative, zero)
- [ ] OPERATOR_SYMBOLS test verifies correct mapping
- [ ] All new tests pass
- [ ] All existing tests pass
- [ ] Phase 15 section added to cursor-prompts/README.md

---

## Commit

```
Add Phase 15 tests and documentation

Unit tests for evaluate_threshold covering all operators and
edge cases. Add Phase 15 section to cursor-prompts README.

Phase 15 Task 5: Tests and Documentation
```
