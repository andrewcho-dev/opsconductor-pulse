# 002: Fix E2E Tests — Routes, Auth, and Component Selectors

## Problem
13 E2E tests fail due to route path changes, auth/token issues, and stale component selectors.

## What to Do

### Part A: Fix Route Assertions (3 tests)

**File: `tests/e2e/test_login_flow.py`**

The frontend router (`frontend/src/app/router.tsx`) uses these actual routes:
- Customer dashboard: `/app/dashboard` (via `/app` parent with `HomeRedirect` → `/dashboard`)
- Operator dashboard: `/app/operator` (via `RequireOperator` guard)
- Root `/` redirects to `/app/` which `HomeRedirect` sends to `/dashboard` or `/operator` based on role

1. `test_customer_login_flow` — Test waits for URL `**/customer/dashboard` but the actual route after login is `/app/dashboard` or just `/app/`.
   - Update URL assertion to: `page.wait_for_url("**/app/dashboard**")` or `page.wait_for_url("**/app/**")`

2. `test_operator_login_flow` — Test waits for URL `**/operator/dashboard` but the actual route is `/app/operator`.
   - Update URL assertion to: `page.wait_for_url("**/app/operator**")`

3. `test_unauthenticated_redirects_to_login` — Test expects redirect to Keycloak (`realms/pulse` in URL). The SPA uses keycloak-js PKCE flow which redirects client-side.
   - Update: navigate to `/app/dashboard`, then wait for either `realms/pulse` in URL OR the Keycloak login form elements (`#username`, `#kc-login`)
   - Increase timeout since client-side redirect adds latency

### Part B: Fix Auth/Token Issues (4 tests)

**File: `tests/e2e/test_integration_crud.py`**

Tests calling the API directly (POST/DELETE `/customer/integrations`) get 403 Forbidden. This is likely because:
1. The CSRF token is missing — the SPA sends `X-CSRF-Token` header. Check if the test fixture includes it.
2. The test may be making direct API calls without going through the authenticated browser session.

**Fix approach:**
- Read how `authenticated_customer_page` fixture works in `tests/e2e/conftest.py`
- If tests make direct `page.request.post()` calls, they need to include the session cookie AND the CSRF token
- Check if the app's CSRF middleware (`services/ui_iot/app.py`) exempts certain paths or requires a specific header
- The simplest fix: make integration CRUD tests use the browser UI (fill forms, click buttons) instead of direct API calls. This is more realistic E2E testing anyway.
- If direct API calls are needed, extract the session cookie from the page context and include `X-CSRF-Token` header

**File: `tests/e2e/test_integrations.py`**
- `test_list_integrations` gets 401 on `GET /customer/integrations`. Same auth issue — needs session cookie from authenticated page context.

### Part C: Fix Component Selectors (4 tests)

**File: `tests/e2e/test_navigation.py`**

1. `test_operator_badge_visible` — looks for `.operator-badge` CSS class.
   - The sidebar uses shadcn's `<Badge>` component which renders with `data-slot="badge"` attribute
   - Read `frontend/src/components/layout/AppSidebar.tsx` to find the exact badge markup
   - Update selector to use `[data-slot='badge']` or `text=Operator` or the Badge's actual rendered class
   - **Working selector pattern** (from passing tests): `page.locator("[data-slot='badge']")`

2. `test_device_detail_has_nav` — looks for `table tbody tr td a` in devices page.
   - Read `frontend/src/features/devices/DeviceListPage.tsx` and `DeviceTable.tsx` for actual table structure
   - The table may use shadcn `<Table>` component with different structure
   - Update selector to match what actually renders (check for `<TableRow>`, `<TableCell>`, link elements)

**File: `tests/e2e/test_customer_dashboard.py`**

3. `test_page_load_dashboard` — looks for `.stats` CSS class.
   - The dashboard likely uses cards/grid layout from shadcn, not a `.stats` class
   - Read `frontend/src/features/dashboard/DashboardPage.tsx` for actual container markup
   - Update to target the actual dashboard content (e.g., `get_by_role("heading")`, or `text=Total Devices` which works in other tests)

**File: `tests/e2e/test_login_flow.py`**

4. `test_logout_flow` — looks for `text=Logout` button.
   - The sidebar logout is likely an icon button (LogOut icon from lucide-react) without visible text
   - Read `frontend/src/components/layout/AppSidebar.tsx` for the logout element
   - Update selector to: `button[title="Logout"]`, `[aria-label="Logout"]`, or use `get_by_role("button", name="Logout")`

### Part D: Fix Subscription UI Tests (2 tests)

**File: `tests/e2e/test_subscription_ui.py`** or **`tests/e2e/test_phase33_features.py`**

1. `test_subscription_page_loads` — looks for `text=Plan Details`. Read `frontend/src/features/subscription/SubscriptionPage.tsx` to find actual text.
2. `test_device_list_shows_limit` — looks for pattern `\d+ of \d+ devices`. Read `DeviceListPage.tsx` to find actual device count display text.

Update assertions to match current UI text.

### Step: Rebuild SPA (if any frontend changes were made)
```bash
cd frontend && npm run build && cd ..
cp -r frontend/dist/* services/ui_iot/spa/
```

### Verify
```bash
RUN_E2E=1 pytest tests/e2e/ -v --tb=short
```

All 85 E2E tests should pass.

## Reference Files
- `tests/e2e/conftest.py` — fixture definitions, auth fixtures login as `customer1`/`test123` and `operator1`/`test123`, session cookie name is `pulse_session`
- `frontend/src/app/router.tsx` — customer routes under `/app`, operator routes under `/app/operator`
- `frontend/src/components/layout/AppSidebar.tsx` — sidebar, logout, operator badge (uses `data-slot` attributes)
- `frontend/src/features/devices/DeviceListPage.tsx` — device table structure
- `frontend/src/features/devices/DeviceTable.tsx` — actual table rendering
- `frontend/src/features/subscription/SubscriptionPage.tsx` — subscription page content
- `frontend/src/features/dashboard/DashboardPage.tsx` — dashboard widgets
- `services/ui_iot/app.py` — CSRF middleware config (search for "csrf")
- `services/ui_iot/middleware/auth.py` — JWT bearer validation

## Rules
- Prefer updating test selectors to match the current UI over changing the UI to match tests
- If a UI element genuinely doesn't exist anymore, skip the test with `@pytest.mark.skip(reason="Feature removed in Phase XX")`
- Add `data-testid` attributes to frontend components only if no reasonable CSS/text selector exists
