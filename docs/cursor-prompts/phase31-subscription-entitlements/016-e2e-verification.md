# 016: E2E Playwright Verification Tests

## Task

Create Playwright E2E tests to verify the Phase 31 subscription UI components.

## File to Create

`tests/e2e/test_subscription_ui.py`

## Test Cases

### 1. Operator Subscription Card

```python
async def test_operator_tenant_subscription_card(authenticated_operator_page):
    """Operator tenant detail page shows subscription card."""
    page = authenticated_operator_page

    # Navigate to Tenants
    await page.click('text=Tenants')
    await page.wait_for_load_state('networkidle')

    # Click first tenant row to go to detail
    await page.locator('table tbody tr').first.click()
    await page.wait_for_load_state('networkidle')

    # Verify Subscription card exists
    subscription_card = page.locator('text=Subscription').first
    await expect(subscription_card).to_be_visible()

    # Verify Manage button exists
    manage_button = page.locator('button:has-text("Manage")')
    await expect(manage_button).to_be_visible()
```

### 2. Operator Edit Subscription Dialog

```python
async def test_operator_edit_subscription_dialog(authenticated_operator_page):
    """Operator can open and use subscription edit dialog."""
    page = authenticated_operator_page

    # Navigate to tenant detail
    await page.click('text=Tenants')
    await page.wait_for_load_state('networkidle')
    await page.locator('table tbody tr').first.click()
    await page.wait_for_load_state('networkidle')

    # Click Manage button
    await page.click('button:has-text("Manage")')

    # Verify dialog opens
    dialog = page.locator('[role="dialog"]')
    await expect(dialog).to_be_visible()

    # Verify quick actions
    await expect(page.locator('button:has-text("+30 Days")')).to_be_visible()
    await expect(page.locator('button:has-text("+90 Days")')).to_be_visible()
    await expect(page.locator('button:has-text("+1 Year")')).to_be_visible()

    # Verify form fields
    await expect(page.locator('label:has-text("Device Limit")')).to_be_visible()
    await expect(page.locator('label:has-text("Term End")')).to_be_visible()
    await expect(page.locator('label:has-text("Status")')).to_be_visible()
    await expect(page.locator('label:has-text("Notes")')).to_be_visible()

    # Verify Save is disabled without notes
    save_button = page.locator('button:has-text("Save Changes")')
    await expect(save_button).to_be_disabled()

    # Fill notes and verify Save becomes enabled
    await page.fill('textarea', 'Test notes for verification')
    await expect(save_button).to_be_enabled()
```

### 3. Customer Subscription Page

```python
async def test_customer_subscription_page(authenticated_customer_page):
    """Customer can view subscription page."""
    page = authenticated_customer_page

    # Navigate to subscription page
    await page.click('text=Subscription')
    await page.wait_for_load_state('networkidle')

    # Verify page header
    await expect(page.locator('h1:has-text("Subscription")')).to_be_visible()

    # Verify Plan Details card
    await expect(page.locator('text=Plan Details')).to_be_visible()
    await expect(page.locator('text=Status')).to_be_visible()

    # Verify Device Usage card
    await expect(page.locator('text=Device Usage')).to_be_visible()
    await expect(page.locator('text=Available')).to_be_visible()
```

### 4. Customer Sidebar Has Subscription Link

```python
async def test_customer_sidebar_subscription_link(authenticated_customer_page):
    """Customer sidebar shows Subscription link."""
    page = authenticated_customer_page

    # Verify sidebar has Subscription link
    sidebar_link = page.locator('a:has-text("Subscription")')
    await expect(sidebar_link).to_be_visible()
```

### 5. Device List Shows Limit

```python
async def test_device_list_shows_limit(authenticated_customer_page):
    """Device list page shows subscription limit info."""
    page = authenticated_customer_page

    # Navigate to devices
    await page.click('text=Devices')
    await page.wait_for_load_state('networkidle')

    # Verify limit display (look for "X of Y devices" pattern)
    limit_text = page.locator('text=/\\d+ of \\d+ devices/')
    await expect(limit_text).to_be_visible()
```

## Full File Structure

```python
import pytest
from playwright.async_api import Page, expect

pytestmark = [pytest.mark.e2e, pytest.mark.asyncio]


class TestOperatorSubscriptionUI:
    """Test operator subscription management UI."""

    async def test_tenant_detail_has_subscription_card(
        self, authenticated_operator_page: Page
    ):
        # ... implementation above

    async def test_edit_subscription_dialog(
        self, authenticated_operator_page: Page
    ):
        # ... implementation above


class TestCustomerSubscriptionUI:
    """Test customer subscription UI."""

    async def test_sidebar_has_subscription_link(
        self, authenticated_customer_page: Page
    ):
        # ... implementation above

    async def test_subscription_page_loads(
        self, authenticated_customer_page: Page
    ):
        # ... implementation above

    async def test_device_list_shows_limit(
        self, authenticated_customer_page: Page
    ):
        # ... implementation above
```

## Running the Tests

```bash
# Set environment variables
export E2E_BASE_URL="https://192.168.10.53"
export KEYCLOAK_URL="https://192.168.10.53"
export RUN_E2E=1

# Run tests
pytest tests/e2e/test_subscription_ui.py -v

# Run with headed browser for debugging
pytest tests/e2e/test_subscription_ui.py -v --headed
```

## Reference

Use patterns from:
- `tests/e2e/conftest.py` - fixtures for authenticated pages
- `tests/e2e/test_operator_dashboard.py` - operator test patterns
- `tests/e2e/test_customer_dashboard.py` - customer test patterns
