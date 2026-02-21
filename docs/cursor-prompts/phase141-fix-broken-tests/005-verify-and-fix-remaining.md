# Task 5: Verify and Fix Remaining Collection Errors

## Context

After completing Tasks 1-4, run the full test suite collection to identify any remaining failures. The env var fixes and dead file deletions should resolve the majority of the 30 broken files, but there may be edge cases.

## Step 1: Run collection check

```bash
pytest tests/unit/ -m unit --co -q 2>&1 | tail -20
```

Expected: "X tests collected" with 0 errors. If there are errors, proceed to Step 2.

## Step 2: Investigate remaining failures

Common remaining issues to look for:

### a) `test_alert_dispatcher.py` / `test_alert_dispatcher_service.py`

These import `services.ui_iot.services.alert_dispatcher`, which in turn does:
```python
from services.snmp_sender import send_alert_trap
```

This should resolve to `services/ui_iot/services/snmp_sender.py` via `sys.path`, but if `pysnmp` is not installed in the test environment, it will fail. Fix: add `pysnmp` to test dependencies or mock the import.

### b) `test_subscription_worker.py`

This file does `sys.path.insert(0, "services/subscription_worker")` then `from worker import ...`. The `worker.py` module imports `aiosmtplib` — if not installed, this will fail. Fix: ensure `aiosmtplib` is in test dependencies or mock the import.

### c) Any `sys.path.insert` pointing at deleted directories

Search for:
```bash
grep -r "delivery_worker\|dispatcher" tests/ --include="*.py"
```

Remove or update any remaining references to deleted services.

## Step 3: Full test run

```bash
pytest -o addopts='' tests/unit/ -m unit -q --tb=short
```

All tests should either pass or skip (no collection errors).

## Step 4: Coverage check

```bash
pytest -o addopts='' tests/unit/ -m unit --cov=services/ui_iot --cov-report=term-missing -q
```

Verify overall coverage has increased now that 30 more test files are collecting.
