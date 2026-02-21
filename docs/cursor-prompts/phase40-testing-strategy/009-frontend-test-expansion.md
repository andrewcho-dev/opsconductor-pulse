# 009: Frontend Test Expansion

## Why
The frontend has only 9 test files with 36 tests (~496 lines). Core pages, the router, and the auth provider have no tests. For a SaaS product, frontend regressions directly impact customer experience.

## Current Frontend Tests (keep and don't break)
- `components/shared/EmptyState.test.tsx` (31 lines)
- `components/shared/PageHeader.test.tsx` (35 lines)
- `components/shared/SeverityBadge.test.tsx` (26 lines)
- `components/shared/StatusBadge.test.tsx` (45 lines)
- `hooks/use-alerts.test.ts` (65 lines)
- `hooks/use-devices.test.ts` (94 lines)
- `hooks/use-users.test.ts` (118 lines)
- `lib/format.test.ts` (26 lines)
- `services/api/client.test.ts` (56 lines)

## Pattern to Follow
Read: `frontend/src/hooks/use-devices.test.ts` — for hook testing with QueryClient wrapper
Read: `frontend/src/components/shared/StatusBadge.test.tsx` — for component rendering tests
Read: `frontend/src/services/api/client.test.ts` — for API client mocking

## Test Files to Create (~36 new tests)

### `frontend/src/app/router.test.tsx` (~8 tests)

Test that routes render the correct components.

```
test_root_redirects_to_dashboard
  - Navigate to "/" → renders dashboard page

test_dashboard_route_renders
  - Navigate to "/dashboard" → renders DashboardPage component

test_devices_route_renders
  - Navigate to "/devices" → renders DeviceListPage

test_device_detail_route_renders
  - Navigate to "/devices/dev-001" → renders DeviceDetailPage

test_operator_route_renders_for_operator
  - User has operator role → "/operator" renders OperatorDevices

test_operator_route_blocked_for_customer
  - User has customer role → "/operator" redirects or shows forbidden

test_integrations_route_renders
  - Navigate to "/integrations" → renders integrations page

test_unknown_route_shows_404
  - Navigate to "/nonexistent" → shows not found page or redirects
```

**Implementation approach:**
- Mock the auth context to provide user with specific roles
- Use `MemoryRouter` from react-router-dom for testing
- Mock page components as simple stubs to avoid needing their full dependency trees
- Focus on testing routing logic, not page content

### `frontend/src/features/devices/DeviceListPage.test.tsx` (~8 tests)

```
test_renders_device_table
  - Mock useDevices to return sample devices
  - Verify table renders with device rows

test_shows_loading_state
  - Mock useDevices with isLoading=true
  - Verify loading indicator shown

test_shows_error_state
  - Mock useDevices with error
  - Verify error message displayed

test_shows_empty_state
  - Mock useDevices to return empty array
  - Verify EmptyState component shown

test_device_count_displayed
  - Mock 5 devices → shows count

test_status_filter_works
  - Mock devices with mixed statuses
  - Select ONLINE filter → only ONLINE devices shown

test_search_filters_devices
  - Type in search box → devices filtered by name/ID

test_click_device_navigates
  - Click device row → navigate called with device ID
```

**Implementation approach:**
- Mock the `use-devices` hook module with `vi.mock`
- Use `render` + `screen` from @testing-library/react
- Wrap in QueryClientProvider and MemoryRouter

### `frontend/src/features/devices/DeviceDetailPage.test.tsx` (~6 tests)

```
test_renders_device_info
  - Mock useDevice to return device data
  - Verify device ID, status, last seen displayed

test_shows_loading
  - isLoading=true → loading indicator

test_shows_not_found
  - useDevice returns null → "Device not found"

test_renders_telemetry_charts
  - Device has telemetry data → chart section rendered

test_renders_alerts_section
  - Device has alerts → alerts section shown

test_back_button_navigates
  - Click back → navigates to device list
```

### `frontend/src/features/operator/OperatorDevices.test.tsx` (~6 tests)

```
test_renders_all_tenant_devices
  - Mock operator devices API → returns cross-tenant device list
  - Verify table shows devices from multiple tenants

test_tenant_column_shown
  - Verify tenant_id column visible (operator view shows tenant)

test_loading_state
  - isLoading=true → loading indicator

test_error_state
  - Error → error message

test_empty_state
  - No devices → empty state message

test_requires_operator_role
  - Component checks role and renders appropriately
```

### `frontend/src/services/auth/AuthProvider.test.tsx` (~8 tests)

```
test_provides_auth_context
  - Wrap children in AuthProvider
  - Children can access useAuth() hook

test_unauthenticated_state
  - Keycloak not authenticated → isAuthenticated=false

test_authenticated_state
  - Mock keycloak.authenticated=true
  - isAuthenticated=true, user object available

test_user_role_extracted
  - Token has realm_access.roles = ["operator"]
  - useAuth().user.role === "operator"

test_tenant_id_extracted
  - Token has organization claim
  - useAuth().user.tenantId extracted correctly

test_is_operator_helper
  - User with operator role → isOperator()=true
  - User with customer role → isOperator()=false

test_logout_calls_keycloak
  - Call logout() → keycloak.logout() invoked

test_token_refresh
  - Mock token near expiry
  - Verify refresh attempted
```

**Implementation approach:**
- Mock `keycloak-js` module with vi.mock
- Create a mock Keycloak instance that returns test tokens
- Test the AuthProvider as a wrapper component

## Implementation Notes

### Test Stack
- **Vitest 4.0.18** with globals (`describe`, `it`, `expect` — no imports needed)
- **@testing-library/react 16.3.2** for rendering and queries
- **@testing-library/user-event 14.6.1** for user interaction simulation
- **@testing-library/jest-dom 6.9.1** for DOM assertions (toBeInTheDocument, etc.)
- **jsdom 28.0.0** as test environment

### Configuration
- `frontend/vitest.config.ts` — environment: jsdom, setup: `./src/setupTests.ts`, include: `src/**/*.test.{ts,tsx}`
- `frontend/src/setupTests.ts` — mocks `window.matchMedia` and `ResizeObserver`
- Vitest globals enabled — no need to import `describe`, `it`, `expect`

### Mocking Patterns (from existing tests)

**Hook testing with React Query:**
```typescript
function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } }
  });
  return ({ children }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
}

const { result } = renderHook(() => useHook(), { wrapper: createWrapper() });
await waitFor(() => expect(result.current.isSuccess).toBe(true));
```

**Module mocking:**
```typescript
vi.mock("@/services/api/devices", () => ({
  fetchDevices: vi.fn(),
  fetchDevice: vi.fn(),
}));
```

**API client mocking:**
```typescript
globalThis.fetch = vi.fn().mockResolvedValue({
  ok: true,
  json: () => Promise.resolve(data),
});
```

### Auth Provider Details
`frontend/src/services/auth/AuthProvider.tsx` uses:
- Keycloak with PKCE (`pkceMethod: "S256"`)
- Token refresh every 30 seconds (refreshes when < 60s remaining)
- Role extraction: `isOperator` = roles include "operator" or "operator-admin"
- User type: `PulseUser` with `sub`, `email`, `tenantId`, `role`, `organization`, `realmAccess`, `name`
- Loading spinner during auth init, error state with retry
- To test: mock `keycloak-js` module entirely with `vi.mock("keycloak-js")`

### Router Details
`frontend/src/app/router.tsx` uses:
- `HomeRedirect` component — routes to `/operator` or `/dashboard` based on role
- `RequireOperator` guard — redirects non-operators to dashboard
- `RequireCustomer` guard — handles cross-role routing
- Route structure: customer routes under `/app`, operator routes under `/app/operator`
- To test: wrap in `MemoryRouter` with `initialEntries`, mock auth context

## Verify
```bash
cd frontend && npm run test -- --run
```

Should show 70+ tests passing (36 new + 36 existing).
