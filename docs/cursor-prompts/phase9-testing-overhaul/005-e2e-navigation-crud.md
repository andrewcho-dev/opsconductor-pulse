# Task 005: E2E Tests — Navigation, Page Rendering, and CRUD Workflows

> **CURSOR: EXECUTE THIS TASK**
>
> Read the instructions below and implement them exactly.
> All tests in this task are E2E tests — they require the full Docker Compose stack running.
> Use Playwright (async API) through the existing E2E test infrastructure.
> RUN THE TESTS in the Test section. Do not proceed if tests fail.

---

## Context

The current E2E tests verify that login works and the dashboard shows data, but they don't verify:
- That every nav link leads to a working HTML page
- That every integration CRUD workflow works through the browser
- That forms validate input and show errors
- That the nav bar appears on every page

These are the tests that would have caught the broken `/customer/devices` and `/customer/alerts` links.

**Read first**:
- `tests/e2e/conftest.py` (Playwright setup, `authenticated_customer_page` fixture)
- `tests/e2e/test_customer_dashboard.py` (existing patterns)
- `tests/e2e/test_integrations.py` (existing integration tests)
- `services/ui_iot/templates/customer/base.html` (nav links to verify)

---

## Task

### 5.1 Create `tests/e2e/test_navigation.py`

Test that every nav link works and every page renders correctly.

```python
pytestmark = [pytest.mark.e2e, pytest.mark.asyncio]
```

**Customer nav link tests** (use `authenticated_customer_page` fixture):

- `test_dashboard_link_works` — click Dashboard nav → page loads, has "Dashboard" heading
- `test_devices_link_returns_html` — click Devices nav → page loads, has "Devices" heading, no raw JSON
- `test_alerts_link_returns_html` — click Alerts nav → page loads, has "Alerts" heading, no raw JSON
- `test_webhooks_link_works` — click Webhooks nav → page loads, has "Webhook" in heading
- `test_snmp_link_works` — click SNMP nav → page loads, has "SNMP" in heading
- `test_email_link_works` — click Email nav → page loads, has "Email" in heading

**Nav bar presence tests**:

- `test_dashboard_has_nav` — dashboard page → nav element present with 6 links
- `test_devices_page_has_nav` — devices page → nav present
- `test_alerts_page_has_nav` — alerts page → nav present
- `test_webhooks_page_has_nav` — webhooks page → nav present
- `test_snmp_page_has_nav` — SNMP page → nav present
- `test_email_page_has_nav` — email page → nav present
- `test_device_detail_has_nav` — device detail page → nav present

**Active nav link tests**:

- `test_dashboard_nav_active` — on dashboard → Dashboard link has active class
- `test_devices_nav_active` — on devices → Devices link has active class
- `test_alerts_nav_active` — on alerts → Alerts link has active class

**Page content verification**:

- `test_devices_page_shows_table` — devices page has a table with device data
- `test_alerts_page_shows_table` — alerts page has a table (may be empty)
- `test_device_detail_shows_device_info` — click device link → detail page loads with device ID

**Cross-page navigation**:

- `test_navigate_dashboard_to_devices_to_detail` — dashboard → devices → click device → detail loads
- `test_navigate_back_button` — detail → browser back → returns to list

**Operator nav tests** (use `authenticated_operator_page` fixture):

- `test_operator_dashboard_has_nav` — operator nav present
- `test_operator_can_see_all_tenants` — dashboard shows devices from multiple tenants

### 5.2 Create `tests/e2e/test_integration_crud.py`

Test full CRUD workflows for each integration type through the browser.

```python
pytestmark = [pytest.mark.e2e, pytest.mark.asyncio]
```

**Webhook CRUD** (use `authenticated_customer_page` fixture):

- `test_create_webhook_integration`:
  1. Navigate to /customer/webhooks
  2. Click "Add Webhook" button
  3. Fill in name and URL
  4. Submit form
  5. Verify integration appears in list
  6. Verify name and URL are displayed correctly

- `test_webhook_form_validates_url`:
  1. Open add form
  2. Submit with empty URL
  3. Verify error message shown

- `test_test_webhook_delivery`:
  1. Create a webhook integration
  2. Click "Test" button
  3. Verify success/failure message appears

- `test_delete_webhook_integration`:
  1. Create a webhook integration
  2. Click "Delete" button
  3. Accept confirmation dialog
  4. Verify integration removed from list

**SNMP CRUD**:

- `test_create_snmp_v2c_integration`:
  1. Navigate to /customer/snmp-integrations
  2. Click "Add SNMP Integration"
  3. Select v2c, fill host/port/community
  4. Submit
  5. Verify appears in list

- `test_create_snmp_v3_integration`:
  1. Select v3 in form
  2. Fill username/auth password
  3. Submit
  4. Verify appears in list

- `test_delete_snmp_integration`:
  1. Create integration
  2. Delete it
  3. Verify removed

**Email CRUD**:

- `test_create_email_integration`:
  1. Navigate to /customer/email-integrations
  2. Click "Add Email Integration"
  3. Fill SMTP host, port, recipients
  4. Submit
  5. Verify appears in list

- `test_delete_email_integration`:
  1. Create integration
  2. Delete it
  3. Verify removed

**Design consistency checks**:

- `test_all_integration_pages_have_same_theme`:
  1. Navigate to each integration page
  2. Check background color of the card/container element
  3. Verify all three use the same color scheme (dark theme)

- `test_all_integration_pages_have_add_button`:
  1. Navigate to each integration page
  2. Verify "Add" button is present and visible

### 5.3 Cleanup helper

Add a helper function to the E2E conftest that creates and tears down test integrations:

```python
@pytest.fixture
async def cleanup_integrations(authenticated_customer_page):
    """Delete all integrations created during test."""
    page = authenticated_customer_page
    created_ids = []
    yield created_ids
    # Cleanup: delete any integrations created during the test
    for integration_id in created_ids:
        try:
            await page.request.delete(f"/customer/integrations/{integration_id}")
        except Exception:
            pass
```

---

## Files to Create/Modify

| Action | Path |
|--------|------|
| CREATE | `tests/e2e/test_navigation.py` |
| CREATE | `tests/e2e/test_integration_crud.py` |
| MODIFY | `tests/e2e/conftest.py` (add cleanup helper) |

---

## Test

```bash
# 1. Ensure full stack is running
cd compose && docker compose up -d && cd ..

# 2. Wait for services
sleep 10

# 3. Run only navigation tests
source compose/.env
KEYCLOAK_URL=http://${HOST_IP}:8180 UI_BASE_URL=http://${HOST_IP}:8080 RUN_E2E=1 pytest tests/e2e/test_navigation.py -v --tb=short

# 4. Run CRUD tests
KEYCLOAK_URL=http://${HOST_IP}:8180 UI_BASE_URL=http://${HOST_IP}:8080 RUN_E2E=1 pytest tests/e2e/test_integration_crud.py -v --tb=short

# 5. Run full E2E suite
KEYCLOAK_URL=http://${HOST_IP}:8180 UI_BASE_URL=http://${HOST_IP}:8080 RUN_E2E=1 pytest tests/e2e/ -v --tb=short
```

---

## Acceptance Criteria

- [ ] `test_navigation.py` has 20+ tests covering every nav link, nav presence, and active state
- [ ] `test_integration_crud.py` has 12+ tests covering create/delete for webhook, SNMP, email
- [ ] Every customer nav link navigates to an HTML page (NEVER raw JSON)
- [ ] Every customer page has the nav bar with all 6 links
- [ ] Active nav link is highlighted on the correct page
- [ ] All three integration pages use the same visual theme
- [ ] Webhook/SNMP/email create+delete workflows work end-to-end in browser
- [ ] All existing E2E tests still pass
- [ ] Total E2E suite runs in < 5 minutes

---

## Commit

```
Add E2E tests for navigation, page rendering, and integration CRUD

- Navigation tests verify every nav link leads to HTML (not JSON)
- Nav bar presence verified on every customer page
- Active link highlighting tested
- Full CRUD workflow tests for webhook, SNMP, and email integrations
- Design consistency check across integration pages

Part of Phase 9: Testing Overhaul
```
