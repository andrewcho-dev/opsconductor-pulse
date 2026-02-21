# Prompt 002 — Run Smoke Suite + Fix Assertion Failures

## Step 1: Collect Tests (no stack needed)

```bash
pytest --collect-only -m "e2e and smoke" tests/e2e/test_smoke.py 2>&1
```

All 10 tests should collect without import errors.

## Step 2: Run Against Live Stack

If the compose stack is running:

```bash
RUN_E2E=true \
UI_BASE_URL=http://localhost:8000 \
KEYCLOAK_URL=http://localhost:8080 \
E2E_BASE_URL=http://localhost:8000 \
pytest -m "e2e and smoke" tests/e2e/test_smoke.py -v --timeout=30 2>&1
```

## Step 3: Fix Any Assertion Failures

Common failure patterns and fixes:

**"locator not visible"** — The selector doesn't match what the page renders.
- Try: `await page.wait_for_selector("h1, h2, main", timeout=5000)`
- Or add `data-testid` attributes to the page components

**"navigation timeout"** — Route doesn't exist, redirects to 404 or login.
- Check the actual URL after navigation: `print(await page.url())`
- Verify the route is registered in the router

**"authentication failed"** — Keycloak not running or credentials changed.
- Check conftest.py for login credentials (customer1/test123)

If a page genuinely doesn't exist, re-add xfail with a clear reason rather than deleting the test.

## Step 4: Verify Unit Tests Unaffected

```bash
pytest -m unit -q 2>&1 | tail -5
```

## Acceptance Criteria

- [ ] All 10 smoke tests either pass OR are documented as xfail with a clear reason
- [ ] No unexpected xpass (a test marked xfail that now passes should have xfail removed)
- [ ] `python -m py_compile tests/e2e/test_smoke.py` — no errors
