# Prompt 004 — Verify Full Unit Suite Passes

## Context

Prompts 001-003 diagnosed and fixed the 58 pre-existing test failures. This prompt verifies the entire unit suite is clean before Phase 43 begins.

## Your Task

### Step 1: Run the full unit suite

```bash
pytest -m unit -v 2>&1 | tee /tmp/phase42-final.txt
```

### Step 2: Evaluate the results

**If 0 failures:** Phase 42 is complete. Report total tests passed.

**If failures remain:** Do NOT move to Phase 43. For each remaining failure:
1. Read the error message carefully
2. Determine if it is:
   - **A new regression introduced by prompts 002/003** — fix it immediately in the same test file
   - **A pre-existing failure in a different test file** — note the file name and failure count
3. Fix any regressions introduced by this phase
4. If there are pre-existing failures in OTHER test files (not the three targeted in this phase), document them in `/tmp/phase42-remaining.txt` with file name + failure count + one-line description of the error

### Step 3: Final run

After fixing any regressions:

```bash
pytest -m unit -v 2>&1 | tail -5
```

Report the final line showing passed/failed counts.

## Acceptance Criteria

- [ ] `pytest -m unit -v` shows 0 failures in the three targeted files:
  - `test_customer_route_handlers.py`
  - `test_operator_route_handlers.py`
  - `test_tenant_middleware.py`
- [ ] No regressions introduced by Phase 42 fixes
- [ ] Any remaining failures in other files are documented in `/tmp/phase42-remaining.txt`
- [ ] Final test count is reported back to the architect

## Gate for Phase 43

**Phase 43 (ui_iot service extraction) must NOT start until this prompt passes.**

The purpose of Phase 43 is to safely extract background tasks from ui_iot. If the test suite is broken, regressions from the extraction will be invisible.
