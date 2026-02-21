# Task 3: Fix Billing Route Tests

## Files to modify
- `tests/unit/test_billing_routes.py` (primary target)
- Any other test file under `tests/unit/` that imports billing routes or uses
  fetchrow-dependent billing endpoints

## What to do

### Step 1 — Run tests and capture failures

```bash
cd /home/opsconductor/simcloud && python -m pytest tests/unit/test_billing_routes.py -v --tb=short 2>&1 | head -80
```

Read the output. Identify which tests fail and what the failure message is.

### Step 2 — Read the test file

Read `tests/unit/test_billing_routes.py` in full.

### Step 3 — Read the route handler

Read `services/ui_iot/routes/billing.py` focusing on:
- What `fetchrow` / `fetch` / `fetchval` calls are made per endpoint
- What columns the returned record needs to have

### Step 4 — Fix each failing test

For each failing test in `test_billing_routes.py`:

1. Add `mock_conn` to the test function signature (it comes from the conftest fixture)
2. Call `mock_conn.set_response("fetchrow", fake_tenant(...))` (or the appropriate
   factory) before making the HTTP request
3. If the route makes multiple DB calls with different expected shapes, use a side_effect
   list instead:
   ```python
   from unittest.mock import AsyncMock
   mock_conn.fetchrow = AsyncMock(side_effect=[
       fake_tenant(),           # first fetchrow call
       fake_device_plan(),      # second fetchrow call
   ])
   ```
4. Import factories at the top of the test file:
   ```python
   from tests.factories import fake_tenant, fake_device_plan, fake_device
   ```

### Step 5 — Verify billing tests pass

```bash
cd /home/opsconductor/simcloud && python -m pytest tests/unit/test_billing_routes.py -v --tb=short 2>&1 | tail -20
```

All billing tests should pass (or show a clear non-DB reason if any remain failing).

### Step 6 — Check overall test count

```bash
cd /home/opsconductor/simcloud && python -m pytest tests/unit/ -q --tb=no 2>&1 | tail -5
```

Record before/after counts.
