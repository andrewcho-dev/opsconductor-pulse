# Task 006: E2E Tests — Visual Regression Baselines

> **CURSOR: EXECUTE THIS TASK**
>
> Read the instructions below and implement them exactly.
> This task sets up Playwright screenshot comparison for visual regression detection.
> RUN THE TESTS in the Test section. Do not proceed if tests fail.

---

## Context

Integration pages were built at different times by different prompts, resulting in inconsistent styling (the email page used Tailwind while others used the dark theme). Task 000 fixed the immediate issues, but there's no automated way to detect future visual regressions. Playwright has built-in screenshot comparison that can catch these.

**Read first**:
- `tests/e2e/conftest.py` (current Playwright setup)
- Playwright docs: `page.screenshot()` and `expect(page).to_have_screenshot()`

---

## Task

### 6.1 Configure screenshot comparison

In `tests/e2e/conftest.py`, add configuration for screenshot comparison:

```python
# Screenshot comparison threshold — allows minor rendering differences
SCREENSHOT_THRESHOLD = 0.1  # 10% pixel difference allowed
```

Create the screenshot baseline directory:
```bash
mkdir -p tests/e2e/screenshots
```

Add `tests/e2e/screenshots/` to `.gitignore` entries are NOT added — baselines should be committed to git so CI can compare against them.

### 6.2 Create `tests/e2e/test_visual_regression.py`

```python
pytestmark = [pytest.mark.e2e, pytest.mark.asyncio]
```

**Customer page baselines**:

- `test_screenshot_customer_dashboard`:
  1. Login as customer1
  2. Navigate to /customer/dashboard
  3. Wait for data to load (wait for device table to be visible)
  4. Take screenshot: `await page.screenshot(path="tests/e2e/screenshots/customer_dashboard.png", full_page=True)`
  5. On subsequent runs, compare: `expect(page).to_have_screenshot("customer_dashboard.png", threshold=0.1)`

- `test_screenshot_customer_devices`:
  1. Navigate to /customer/devices
  2. Wait for device table
  3. Capture/compare screenshot

- `test_screenshot_customer_alerts`:
  1. Navigate to /customer/alerts
  2. Wait for content
  3. Capture/compare screenshot

- `test_screenshot_webhook_integrations`:
  1. Navigate to /customer/webhooks
  2. Wait for content
  3. Capture/compare screenshot

- `test_screenshot_snmp_integrations`:
  1. Navigate to /customer/snmp-integrations
  2. Wait for content
  3. Capture/compare screenshot

- `test_screenshot_email_integrations`:
  1. Navigate to /customer/email-integrations
  2. Wait for content
  3. Capture/compare screenshot

- `test_screenshot_device_detail`:
  1. Navigate to a device detail page
  2. Wait for content
  3. Capture/compare screenshot

**Operator page baselines**:

- `test_screenshot_operator_dashboard`:
  1. Login as operator1
  2. Navigate to /operator/dashboard
  3. Capture/compare screenshot

**Consistency checks** (programmatic, not screenshot):

- `test_integration_pages_same_background`:
  1. Navigate to each integration page
  2. Get computed background-color of the main content area
  3. Assert all three are the same value

- `test_integration_pages_same_font`:
  1. Navigate to each integration page
  2. Get computed font-family of the body
  3. Assert all three are the same value

- `test_integration_pages_same_button_style`:
  1. Navigate to each integration page
  2. Get computed background-color of the "Add" button
  3. Assert all three are the same value

### 6.3 First-run baseline generation

On the first run, Playwright screenshot comparison creates the baselines. Document the workflow:

1. First run: `RUN_E2E=1 pytest tests/e2e/test_visual_regression.py -v --update-snapshots`
   — generates baseline screenshots in `tests/e2e/test_visual_regression-snapshots/`
2. Commit the baselines to git
3. Subsequent runs: `RUN_E2E=1 pytest tests/e2e/test_visual_regression.py -v`
   — compares current screenshots against baselines
4. When intentional UI changes are made: re-run with `--update-snapshots` and commit new baselines

### 6.4 Add snapshot directory to version control

Ensure the Playwright snapshot directory is tracked by git:
- Do NOT add `tests/e2e/test_visual_regression-snapshots/` to `.gitignore`
- This directory contains the baseline images that CI compares against

If a `.gitignore` in `tests/e2e/` exists, make sure it doesn't exclude `*-snapshots/`.

---

## Files to Create/Modify

| Action | Path |
|--------|------|
| CREATE | `tests/e2e/test_visual_regression.py` |
| MODIFY | `tests/e2e/conftest.py` (add screenshot config if needed) |

---

## Test

```bash
# 1. Ensure full stack is running
cd compose && docker compose up -d && cd ..
sleep 10

# 2. Generate baselines (first run)
source compose/.env
KEYCLOAK_URL=http://${HOST_IP}:8180 UI_BASE_URL=http://${HOST_IP}:8080 RUN_E2E=1 pytest tests/e2e/test_visual_regression.py -v --update-snapshots

# 3. Run again to verify comparison works (should all pass — nothing changed)
KEYCLOAK_URL=http://${HOST_IP}:8180 UI_BASE_URL=http://${HOST_IP}:8080 RUN_E2E=1 pytest tests/e2e/test_visual_regression.py -v

# 4. Run full E2E suite
KEYCLOAK_URL=http://${HOST_IP}:8180 UI_BASE_URL=http://${HOST_IP}:8080 RUN_E2E=1 pytest tests/e2e/ -v
```

---

## Acceptance Criteria

- [ ] `test_visual_regression.py` captures screenshots for all 8 customer/operator pages
- [ ] Baseline screenshots generated and committed to git
- [ ] Second run compares against baselines and passes
- [ ] Programmatic consistency checks verify same background, font, button styles across integration pages
- [ ] All existing E2E tests still pass
- [ ] Documentation in the test file explains how to update baselines

---

## Commit

```
Add visual regression tests with Playwright screenshots

- Baseline screenshots for all 8 customer/operator pages
- Programmatic checks for integration page design consistency
  (background color, font, button styling)
- Screenshots committed as baselines for future comparison
- Run with --update-snapshots to regenerate after intentional changes

Part of Phase 9: Testing Overhaul
```
