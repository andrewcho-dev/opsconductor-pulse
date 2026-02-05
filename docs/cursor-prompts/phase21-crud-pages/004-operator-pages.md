# Task 004: Operator Pages — Dashboard, Devices, Audit Log, Settings

> **CURSOR: EXECUTE THIS TASK**
>
> Read the instructions below and implement them exactly.
> Create/modify only the files listed in "Files to Create/Modify".
> RUN THE TESTS in the Test section. Do not proceed if tests fail.
> IMPORTANT: Do not commit until all tests pass.

---

## Context

Task 1 created API functions and hooks for operator endpoints. This task implements the four operator pages. Operator pages show cross-tenant data — they use `/operator/*` endpoints which bypass RLS and log all access to the audit trail.

**Important**: Only users with `isOperator` (role = `operator` or `operator_admin`) can access these pages. The sidebar already conditionally shows operator nav links based on `isOperator`.

**Read first**:
- `frontend/src/features/operator/OperatorDashboard.tsx` — current stub
- `frontend/src/features/operator/OperatorDevices.tsx` — current stub
- `frontend/src/features/operator/AuditLogPage.tsx` — current stub
- `frontend/src/features/operator/SettingsPage.tsx` — current stub
- `frontend/src/hooks/use-operator.ts` — operator hooks from Task 1
- `frontend/src/services/api/types.ts` — operator types (OperatorDevicesResponse, etc.)
- `frontend/src/components/layout/AppSidebar.tsx` — operator nav section

---

## Task

### 4.1 Implement OperatorDashboard

**File**: `frontend/src/features/operator/OperatorDashboard.tsx` (REPLACE)

The operator dashboard shows a cross-tenant overview composed from multiple API calls. Layout:

1. **PageHeader**: "Operator Dashboard" with description "Cross-tenant system overview"
2. **Stat cards** (4 cards in a responsive grid):
   - Total Devices (from `/operator/devices?limit=1` count or fetch a small set)
   - Online Devices (count devices with status ONLINE)
   - Open Alerts (from `/operator/alerts?status=OPEN&limit=1` count)
   - Quarantine Events (from `/operator/quarantine?minutes=60&limit=1` count)
3. **Two-column grid**:
   - Left: Recent open alerts table (top 10, with tenant_id column)
   - Right: Recent quarantine events table (top 10, with reason column)

Implementation approach:
- Call `useOperatorDevices(undefined, 500)` to get all devices for counting
- Call `useOperatorAlerts("OPEN", undefined, 20)` for open alerts
- Call `useQuarantine(60, 20)` for recent quarantine
- Count online/stale from the devices array
- Wrap sections in WidgetErrorBoundary

Key differences from customer dashboard:
- Shows `tenant_id` column in tables (cross-tenant view)
- Shows quarantine section (not visible to customers)
- No WebSocket integration (operator views use polling via TanStack Query)
- Device links: do NOT link to `/devices/{id}` (those are customer pages). Just show device ID as text.

### 4.2 Implement OperatorDevices

**File**: `frontend/src/features/operator/OperatorDevices.tsx` (REPLACE)

A cross-tenant device table with optional tenant filtering.

1. **PageHeader**: "All Devices" with tenant filter input
2. **Tenant filter**: A text input that filters by tenant_id. Add a "Filter" button next to it. When clicked, refetch with the tenant filter. Add a "Clear" button to remove the filter.
3. **Device table** with columns:
   - Tenant ID
   - Device ID
   - Site ID
   - Status (StatusBadge)
   - Last Seen
   - Battery (from state.battery_pct)
4. **Pagination** using offset/limit (same pattern as customer DeviceListPage)
5. Loading/empty/error states

Use `useOperatorDevices(tenantFilter, limit, offset)` hook. The tenant filter is stored in local state and applied when the user clicks Filter.

### 4.3 Implement AuditLogPage

**File**: `frontend/src/features/operator/AuditLogPage.tsx` (REPLACE)

The operator audit log shows all operator access events. Only available to `operator_admin` role.

1. **PageHeader**: "Audit Log"
2. **Filter bar**: Optional filters (all in a horizontal row):
   - User ID — text input
   - Action — text input
   - "Filter" button + "Clear" button
3. **Audit log table** with columns:
   - Timestamp (created_at, formatted)
   - User ID
   - Action
   - Tenant Filter (if present)
   - Resource (type + id combined, if present)
   - RLS Bypassed (badge: yes/no)
4. Loading/empty states

Use `useAuditLog(userId, action, since, limit)` hook. Filters stored in local state, applied on "Filter" click.

**Role check**: If the user's role is `operator` (not `operator_admin`), show an access denied message: "Audit log requires operator_admin role."

### 4.4 Implement SettingsPage

**File**: `frontend/src/features/operator/SettingsPage.tsx` (REPLACE)

A simple settings form for system configuration. Only available to `operator_admin` role.

Since the backend settings GET endpoint returns HTML (no JSON format), implement this page as a simple form that shows the available settings and lets the user update them.

1. **PageHeader**: "System Settings"
2. **Settings form** (Card layout):
   - **Mode** — select: "PROD" or "DEV"
   - **Store Rejects** — switch toggle (only enabled in DEV mode)
   - **Mirror Rejects** — switch toggle (only enabled in DEV mode)
   - When Mode is "PROD", Store Rejects and Mirror Rejects are forced to Off and disabled
   - "Save" button calls `updateOperatorSettings()`
3. **Info card**: Brief explanation of each setting

The form uses local state initialized with sensible defaults (PROD mode, rejects off). On submit, POST to `/operator/settings`.

**Note on backend compatibility**: The backend POST `/operator/settings` expects form data (`Form(...)` parameters), not JSON. The `apiPost` function sends JSON. To handle this, create a custom fetch call in the settings page that sends form data:

```typescript
async function saveSettings(data: { mode: string; store_rejects: string; mirror_rejects: string }) {
  const formData = new URLSearchParams();
  formData.set("mode", data.mode);
  formData.set("store_rejects", data.store_rejects);
  formData.set("mirror_rejects", data.mirror_rejects);

  const headers = await getAuthHeaders(); // Import from api/client
  const resp = await fetch("/operator/settings", {
    method: "POST",
    headers: { ...headers, "Content-Type": "application/x-www-form-urlencoded" },
    body: formData.toString(),
  });
  if (!resp.ok) throw new Error("Failed to save settings");
}
```

Alternatively, you can import `keycloak` from `@/services/auth/keycloak` and construct the Authorization header directly. The key point is that this POST must use `application/x-www-form-urlencoded`, not `application/json`.

After successful save, show a brief success message ("Settings saved").

**Role check**: If the user's role is `operator` (not `operator_admin`), show an access denied message.

---

## Files to Create/Modify

| Action | Path | What |
|--------|------|------|
| MODIFY | `frontend/src/features/operator/OperatorDashboard.tsx` | Cross-tenant overview (replace stub) |
| MODIFY | `frontend/src/features/operator/OperatorDevices.tsx` | Cross-tenant device table (replace stub) |
| MODIFY | `frontend/src/features/operator/AuditLogPage.tsx` | Audit log with filters (replace stub) |
| MODIFY | `frontend/src/features/operator/SettingsPage.tsx` | Settings form (replace stub) |

---

## Test

### Step 1: Verify build

```bash
cd /home/opsconductor/simcloud/frontend && npm run build
```

### Step 2: Verify TypeScript

```bash
cd /home/opsconductor/simcloud/frontend && npx tsc --noEmit
```

### Step 3: Verify implementation

Read the files and confirm:
- [ ] OperatorDashboard has stat cards (devices, alerts, quarantine counts)
- [ ] OperatorDashboard has alerts table and quarantine table with tenant_id column
- [ ] OperatorDevices has tenant filter input with Filter/Clear buttons
- [ ] OperatorDevices table shows tenant_id, device_id, site_id, status, last_seen, battery
- [ ] OperatorDevices has pagination
- [ ] AuditLogPage checks for operator_admin role
- [ ] AuditLogPage has user/action filter inputs
- [ ] AuditLogPage table shows timestamp, user, action, tenant, resource, RLS bypass
- [ ] SettingsPage checks for operator_admin role
- [ ] SettingsPage has mode select and reject toggles
- [ ] SettingsPage disables reject toggles in PROD mode
- [ ] SettingsPage submits form data (not JSON) to /operator/settings
- [ ] All pages have loading/empty/error states

### Step 4: Verify backend tests

```bash
cd /home/opsconductor/simcloud && python3 -m pytest tests/unit/ -v -x
```

---

## Acceptance Criteria

- [ ] Operator dashboard with cross-tenant stats and tables
- [ ] Operator devices with tenant filter and pagination
- [ ] Audit log with role-gated access and filtering
- [ ] Settings page with mode/rejects form
- [ ] Settings POST uses form encoding (not JSON)
- [ ] operator_admin role required for audit log and settings
- [ ] tenant_id visible in operator tables (cross-tenant)
- [ ] No device links to customer routes from operator pages
- [ ] Loading/empty/error states on all pages
- [ ] `npm run build` succeeds
- [ ] All Python tests pass

---

## Commit

```
Implement operator dashboard, devices, audit log, and settings

Cross-tenant operator dashboard with device/alert/quarantine
stats. Device table with tenant filtering and pagination.
Audit log with role-gated access. Settings form for system
mode and reject policies.

Phase 21 Task 4: Operator Pages
```
