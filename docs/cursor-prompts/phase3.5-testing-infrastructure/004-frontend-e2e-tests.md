# Task 004: Frontend E2E Tests

> **CURSOR: EXECUTE THIS TASK**
>
> This is an implementation task. Read the instructions below and implement them.
> Modify the files listed in "Files to Create/Modify" section.
> Follow the acceptance criteria to verify your work.
> Commit with the message in the "Commit" section when done.

---

## Context

We need end-to-end tests that verify the full user experience: login, navigation, CRUD operations, and logout. Playwright is the recommended tool for modern E2E testing.

**Read first**:
- `services/ui_iot/templates/` (frontend templates)
- `services/ui_iot/static/js/auth.js` (auth handling)
- Playwright documentation: https://playwright.dev/python/

**Depends on**: Tasks 001, 002, 003

## Task

### 4.1 Install Playwright

Add to `requirements-test.txt` or `services/ui_iot/requirements.txt`:

```
playwright>=1.40.0
pytest-playwright>=0.4.0
```

Install browsers:
```bash
playwright install chromium
```

### 4.2 Create Playwright configuration

Create `playwright.config.py` in project root:

```python
from playwright.sync_api import Playwright

def pytest_configure(config):
    """Configure Playwright for pytest."""
    pass
```

Or use `pytest.ini` additions:

```ini
[pytest]
# ... existing config ...
playwright_browser = chromium
playwright_headless = true
```

### 4.3 Create E2E conftest

Create `tests/e2e/conftest.py`:

```python
import pytest
from playwright.async_api import async_playwright, Browser, Page, BrowserContext
import os

BASE_URL = os.getenv("E2E_BASE_URL", "http://localhost:8080")
KEYCLOAK_URL = os.getenv("KEYCLOAK_URL", "http://localhost:8180")


@pytest.fixture(scope="session")
async def browser():
    """Create browser instance."""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        yield browser
        await browser.close()


@pytest.fixture
async def context(browser: Browser):
    """Create browser context with fresh state."""
    context = await browser.new_context(
        viewport={"width": 1280, "height": 720},
        base_url=BASE_URL,
    )
    yield context
    await context.close()


@pytest.fixture
async def page(context: BrowserContext):
    """Create page."""
    page = await context.new_page()
    yield page
    await page.close()


@pytest.fixture
async def authenticated_customer_page(context: BrowserContext):
    """Create page with customer1 logged in."""
    page = await context.new_page()

    # Navigate to app
    await page.goto("/")

    # Should redirect to /login then Keycloak
    await page.wait_for_url(f"{KEYCLOAK_URL}/**")

    # Fill login form
    await page.fill("#username", "customer1")
    await page.fill("#password", "test123")
    await page.click("#kc-login")

    # Wait for redirect back to app
    await page.wait_for_url(f"{BASE_URL}/customer/dashboard")

    yield page
    await page.close()


@pytest.fixture
async def authenticated_operator_page(context: BrowserContext):
    """Create page with operator1 logged in."""
    page = await context.new_page()

    await page.goto("/")
    await page.wait_for_url(f"{KEYCLOAK_URL}/**")
    await page.fill("#username", "operator1")
    await page.fill("#password", "test123")
    await page.click("#kc-login")
    await page.wait_for_url(f"{BASE_URL}/operator/dashboard")

    yield page
    await page.close()
```

### 4.4 Create login flow tests

Create `tests/e2e/test_login_flow.py`:

```python
import pytest
from playwright.async_api import Page, expect

pytestmark = [pytest.mark.e2e, pytest.mark.asyncio]

KEYCLOAK_URL = "http://localhost:8180"


class TestLoginFlow:
    """Test OAuth login flow."""

    async def test_unauthenticated_redirects_to_login(self, page: Page):
        """Unauthenticated user redirected to Keycloak."""
        await page.goto("/")

        # Should redirect through /login to Keycloak
        await page.wait_for_url(f"{KEYCLOAK_URL}/**", timeout=10000)
        assert "realms/pulse" in page.url

    async def test_customer_login_flow(self, page: Page):
        """Customer can login and reach dashboard."""
        await page.goto("/")
        await page.wait_for_url(f"{KEYCLOAK_URL}/**")

        # Fill Keycloak login
        await page.fill("#username", "customer1")
        await page.fill("#password", "test123")
        await page.click("#kc-login")

        # Wait for redirect to customer dashboard
        await page.wait_for_url("**/customer/dashboard", timeout=10000)

        # Verify on customer dashboard
        assert "/customer/dashboard" in page.url

        # Check tenant badge visible
        tenant_badge = page.locator(".tenant-badge")
        await expect(tenant_badge).to_be_visible()
        await expect(tenant_badge).to_contain_text("tenant-a")

    async def test_operator_login_flow(self, page: Page):
        """Operator can login and reach operator dashboard."""
        await page.goto("/")
        await page.wait_for_url(f"{KEYCLOAK_URL}/**")

        await page.fill("#username", "operator1")
        await page.fill("#password", "test123")
        await page.click("#kc-login")

        await page.wait_for_url("**/operator/dashboard", timeout=10000)
        assert "/operator/dashboard" in page.url

        # Check operator badge visible
        operator_badge = page.locator(".operator-badge")
        await expect(operator_badge).to_be_visible()

    async def test_invalid_login_shows_error(self, page: Page):
        """Invalid credentials show error."""
        await page.goto("/")
        await page.wait_for_url(f"{KEYCLOAK_URL}/**")

        await page.fill("#username", "customer1")
        await page.fill("#password", "wrongpassword")
        await page.click("#kc-login")

        # Should stay on Keycloak with error
        error = page.locator("#input-error")
        await expect(error).to_be_visible()

    async def test_logout_flow(self, authenticated_customer_page: Page):
        """User can logout."""
        page = authenticated_customer_page

        # Click logout
        await page.click("text=Logout")

        # Should redirect to Keycloak logout then home
        await page.wait_for_url("**/", timeout=10000)

        # Verify logged out by trying to access protected route
        await page.goto("/customer/dashboard")
        await page.wait_for_url(f"{KEYCLOAK_URL}/**", timeout=10000)
```

### 4.5 Create customer dashboard tests

Create `tests/e2e/test_customer_dashboard.py`:

```python
import pytest
from playwright.async_api import Page, expect

pytestmark = [pytest.mark.e2e, pytest.mark.asyncio]


class TestCustomerDashboard:
    """Test customer dashboard functionality."""

    async def test_dashboard_shows_device_stats(
        self, authenticated_customer_page: Page
    ):
        """Dashboard shows device statistics."""
        page = authenticated_customer_page

        # Wait for stats to load
        stats = page.locator(".stats")
        await expect(stats).to_be_visible()

        # Check stat cards exist
        await expect(page.locator("text=Total Devices")).to_be_visible()
        await expect(page.locator("text=Online")).to_be_visible()
        await expect(page.locator("text=Stale")).to_be_visible()

    async def test_dashboard_shows_devices_table(
        self, authenticated_customer_page: Page
    ):
        """Dashboard shows devices table."""
        page = authenticated_customer_page

        # Check devices table exists
        table = page.locator("table").first
        await expect(table).to_be_visible()

        # Check headers
        await expect(page.locator("th:has-text('Device ID')")).to_be_visible()
        await expect(page.locator("th:has-text('Status')")).to_be_visible()

    async def test_device_link_navigates_to_detail(
        self, authenticated_customer_page: Page
    ):
        """Clicking device navigates to detail page."""
        page = authenticated_customer_page

        # Click first device link
        device_link = page.locator("table tbody tr td a").first
        device_id = await device_link.inner_text()
        await device_link.click()

        # Wait for navigation
        await page.wait_for_url("**/customer/devices/**")
        assert device_id in page.url

    async def test_shows_only_tenant_data(
        self, authenticated_customer_page: Page
    ):
        """Dashboard only shows current tenant's data."""
        page = authenticated_customer_page

        # Check tenant badge
        tenant_badge = page.locator(".tenant-badge")
        await expect(tenant_badge).to_contain_text("tenant-a")

        # All visible device rows should not have tenant-b
        device_rows = page.locator("table tbody tr")
        count = await device_rows.count()

        for i in range(count):
            row = device_rows.nth(i)
            row_text = await row.inner_text()
            assert "tenant-b" not in row_text


class TestCustomerDeviceDetail:
    """Test device detail page."""

    async def test_device_detail_loads(
        self, authenticated_customer_page: Page
    ):
        """Device detail page loads correctly."""
        page = authenticated_customer_page

        # Navigate to a device
        device_link = page.locator("table tbody tr td a").first
        await device_link.click()
        await page.wait_for_url("**/customer/devices/**")

        # Check page elements
        await expect(page.locator("h1, h2")).to_be_visible()

    async def test_cannot_access_other_tenant_device(
        self, authenticated_customer_page: Page
    ):
        """Cannot access device from another tenant."""
        page = authenticated_customer_page

        # Try to access tenant-b device directly
        await page.goto("/customer/devices/test-device-b1")

        # Should show 404 or error
        # Check for error indication
        content = await page.content()
        assert "404" in content or "not found" in content.lower()
```

### 4.6 Create integration management tests

Create `tests/e2e/test_integrations.py`:

```python
import pytest
from playwright.async_api import Page, expect
import uuid

pytestmark = [pytest.mark.e2e, pytest.mark.asyncio]


class TestIntegrationManagement:
    """Test integration CRUD via UI (if UI exists) or API."""

    async def test_create_integration_via_api(
        self, authenticated_customer_page: Page
    ):
        """Create integration via API call."""
        page = authenticated_customer_page

        # Get cookies for API call
        cookies = await page.context.cookies()
        session_cookie = next(
            (c for c in cookies if c["name"] == "pulse_session"),
            None
        )

        if session_cookie:
            # Make API request
            response = await page.request.post(
                "/customer/integrations",
                data={
                    "name": f"E2E Test Integration {uuid.uuid4().hex[:8]}",
                    "webhook_url": "https://webhook.site/test",
                    "enabled": True,
                },
            )
            assert response.status == 201

    async def test_list_integrations(
        self, authenticated_customer_page: Page
    ):
        """List integrations via API."""
        page = authenticated_customer_page

        response = await page.request.get("/customer/integrations")
        assert response.status == 200

        data = await response.json()
        assert "integrations" in data
```

### 4.7 Create operator dashboard tests

Create `tests/e2e/test_operator_dashboard.py`:

```python
import pytest
from playwright.async_api import Page, expect

pytestmark = [pytest.mark.e2e, pytest.mark.asyncio]


class TestOperatorDashboard:
    """Test operator dashboard functionality."""

    async def test_shows_all_tenants(
        self, authenticated_operator_page: Page
    ):
        """Operator dashboard shows data from all tenants."""
        page = authenticated_operator_page

        # Check for tenant column in tables
        await expect(page.locator("th:has-text('Tenant')")).to_be_visible()

    async def test_operator_badge_visible(
        self, authenticated_operator_page: Page
    ):
        """Operator badge is visible."""
        page = authenticated_operator_page

        badge = page.locator(".operator-badge")
        await expect(badge).to_be_visible()
        await expect(badge).to_contain_text("OPERATOR")

    async def test_settings_not_visible_for_regular_operator(
        self, authenticated_operator_page: Page
    ):
        """Regular operator cannot see settings panel."""
        page = authenticated_operator_page

        # Settings panel should not be visible (operator1 is not admin)
        settings = page.locator(".settings-panel")
        await expect(settings).not_to_be_visible()
```

## Files to Create/Modify

| Action | Path |
|--------|------|
| MODIFY | `services/ui_iot/requirements.txt` (add playwright, pytest-playwright) |
| CREATE | `tests/e2e/conftest.py` |
| CREATE | `tests/e2e/test_login_flow.py` |
| CREATE | `tests/e2e/test_customer_dashboard.py` |
| CREATE | `tests/e2e/test_integrations.py` |
| CREATE | `tests/e2e/test_operator_dashboard.py` |

## Acceptance Criteria

- [ ] Playwright installed and configured
- [ ] Login flow tests pass
- [ ] Customer dashboard tests pass
- [ ] Operator dashboard tests pass
- [ ] Session handling works correctly
- [ ] Tenant isolation verified in UI

**Prerequisites**:
- All services running: `docker compose up -d`
- Keycloak healthy with test users
- UI container rebuilt with latest code

**Run tests**:
```bash
# Install Playwright browsers
playwright install chromium

# Run E2E tests
pytest tests/e2e/ -v -m e2e
```

## Commit

```
Add frontend E2E tests with Playwright

- Playwright configuration and fixtures
- Login flow tests (customer, operator, logout)
- Customer dashboard tests
- Operator dashboard tests
- Integration management tests
- Authenticated page fixtures

Part of Phase 3.5: Testing Infrastructure
```
