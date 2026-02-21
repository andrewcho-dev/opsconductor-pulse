# 135-003: Operator Table Pages

## Task
Convert 3 operator-facing table pages from raw `<table>` to `DataTable`. Evaluate whether TenantHealthMatrix is a good fit.

---

## 1. UserListPage (Operator)
**File**: `frontend/src/features/operator/UserListPage.tsx`

This is the operator-level user management table (different from the customer UsersPage which already uses DataTable).

Define columns:
- `username` (sortable) — username, bold. Show first_name + last_name below as `text-xs text-muted-foreground`
- `email` (sortable) — email text
- `realm_roles` / `roles` (sortable) — Badge for primary role (operator-admin, operator, customer, etc.)
- `enabled` (sortable) — Badge: Active (default) / Disabled (secondary)
- `created_at` (sortable) — formatted date if available
- `actions` (non-sortable) — DropdownMenu with Edit, Assign Role, Assign Tenant, Disable/Enable actions

If the API supports pagination (offset/limit), use server-side pagination:
```typescript
const [page, setPage] = useState(1);
const limit = 50;
const offset = (page - 1) * limit;
const { data, isLoading } = useOperatorUsers(search, limit, offset);
// Pass totalCount, pagination, onPaginationChange to DataTable
```

If the API returns all users at once, use client-side (no pagination props).

**Empty state**: "No users found."

---

## 2. CertificateOverviewPage (Operator)
**File**: `frontend/src/features/operator/CertificateOverviewPage.tsx`

Fleet-wide certificate overview table for operators.

Define columns:
- `tenant_id` (sortable) — tenant name or ID
- `device_id` (sortable) — device ID, monospace
- `common_name` (sortable) — certificate CN
- `status` (sortable) — Badge: ACTIVE=default, REVOKED=destructive, EXPIRED=secondary
- `not_after` (sortable) — expiry date, red text if expired or expiring within 30 days
- `fingerprint_sha256` (non-sortable) — truncated fingerprint
- `actions` (non-sortable) — View details link

**Empty state**: "No device certificates found across tenants."
**Pagination**: Server-side if the API supports it (operator endpoints typically handle large datasets).

---

## 3. TenantHealthMatrix
**File**: `frontend/src/features/operator/TenantHealthMatrix.tsx`

**Evaluate fit**: The TenantHealthMatrix is likely a grid/matrix layout showing health indicators per tenant across multiple dimensions (devices, alerts, connectivity, etc.).

**Decision criteria**:
- If it renders as a standard rows-and-columns table with tenant rows and metric columns → convert to DataTable
- If it uses a custom grid/card layout, color-coded cells, or sparklines that don't map to standard table columns → keep the current layout and add a comment explaining why DataTable was not used

**If converting**, define columns:
- `tenant_name` (sortable) — tenant display name
- `device_count` (sortable) — total devices
- `online_count` (sortable) — online devices (green text)
- `alert_count` (sortable) — open alerts (red if > 0)
- `health_score` (sortable) — percentage or status indicator

**If NOT converting**, add this comment at the top of the component:
```typescript
// DataTable not used: TenantHealthMatrix uses a custom grid layout with
// color-coded cells and visual indicators that don't map to standard table columns.
```

---

## Verification
```bash
cd frontend && npm run build
npx tsc --noEmit
```
Navigate to operator pages (/operator/users, /operator/certificates) and verify tables work correctly.
