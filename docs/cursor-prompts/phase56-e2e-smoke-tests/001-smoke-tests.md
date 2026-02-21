# Prompt 001 — Smoke Test File

Read `tests/e2e/conftest.py` fully to understand available fixtures, base URLs, and existing patterns.
Read one existing test file (e.g., `tests/e2e/test_navigation.py`) to understand test style.

## Create `tests/e2e/test_smoke.py`

All tests marked `@pytest.mark.e2e` and `@pytest.mark.smoke`.

### Group 1: Stack Health (no browser — use httpx)

```python
import httpx
import os
import pytest

UI_BASE_URL = os.environ.get("UI_BASE_URL", "http://localhost:8000")
HEALTHZ_URLS = {
    "ui_iot": f"{UI_BASE_URL}/healthz",
    # Add other services if their ports are exposed in docker-compose
}

@pytest.mark.e2e
@pytest.mark.smoke
@pytest.mark.asyncio
async def test_ui_iot_healthz():
    """ui_iot /healthz returns 200 with status=ok or status=degraded (not error)."""
    async with httpx.AsyncClient(timeout=5.0) as client:
        resp = await client.get(HEALTHZ_URLS["ui_iot"])
    assert resp.status_code == 200
    data = resp.json()
    assert data.get("status") in ("ok", "degraded")
```

### Group 2: Unauthenticated API Returns 401

```python
@pytest.mark.e2e
@pytest.mark.smoke
@pytest.mark.asyncio
async def test_unauthenticated_api_returns_401():
    """Direct API call without token returns 401."""
    async with httpx.AsyncClient(timeout=5.0) as client:
        resp = await client.get(f"{UI_BASE_URL}/customer/devices")
    assert resp.status_code == 401
```

### Group 3: Page Load Tests (use authenticated_customer_page fixture)

For each page, write a test that:
1. Navigates to the URL
2. Waits for the page to finish loading (no spinner visible, or specific element present)
3. Asserts no error message is shown

Pages to test:
- `/` (dashboard) — assert some heading or "Dashboard" text visible
- `/devices` — assert device table or "No devices" text visible
- `/alerts` — assert page heading visible
- `/sites` — assert page heading visible
- `/integrations` — assert page heading visible
- `/delivery-log` — assert page heading visible

Pattern for each:
```python
@pytest.mark.e2e
@pytest.mark.smoke
async def test_dashboard_loads(customer_page):
    await customer_page.goto(f"{UI_BASE_URL}/")
    await customer_page.wait_for_load_state("networkidle")
    # Assert key element visible
    assert await customer_page.locator("h1, h2, [data-testid='dashboard']").first.is_visible()
```

### Group 4: Operator Login

```python
@pytest.mark.e2e
@pytest.mark.smoke
async def test_operator_dashboard_loads(operator_page):
    await operator_page.goto(f"{UI_BASE_URL}/operator")
    await operator_page.wait_for_load_state("networkidle")
    assert await operator_page.locator("h1, h2").first.is_visible()
```

### Group 5: Alert Rule Form Navigation

```python
@pytest.mark.e2e
@pytest.mark.smoke
async def test_alert_rule_create_form_loads(customer_page):
    """Can navigate to alert rule create form without error."""
    await customer_page.goto(f"{UI_BASE_URL}/alert-rules/new")
    await customer_page.wait_for_load_state("networkidle")
    # Assert form fields visible
    assert await customer_page.locator("input, select, form").first.is_visible()
```

## Notes

- Use `wait_for_load_state("networkidle")` consistently
- Do NOT create or modify data — smoke tests are read-only
- If a page doesn't exist yet in the router, the test should be marked `@pytest.mark.xfail(reason="page not yet implemented")` rather than removed
- Timeout budget: each test should complete in < 10 seconds

## Acceptance Criteria

- [ ] `tests/e2e/test_smoke.py` exists with all tests above
- [ ] All tests marked `@pytest.mark.e2e` AND `@pytest.mark.smoke`
- [ ] Tests are non-destructive (no data writes)
- [ ] File imports cleanly (`python -c "import tests.e2e.test_smoke"` or pytest collection passes)
