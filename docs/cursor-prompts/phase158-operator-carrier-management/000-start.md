# Phase 158 — Operator Carrier Management Panel

## Goal

Give operator-role users a dedicated page at `/operator/carriers` to view, create, edit, and delete carrier integrations across all tenants. The existing `/settings/carrier` route is gated behind `RequireCustomer` and scoped to one tenant; operators need cross-tenant visibility with optional filtering.

## Execution Order

| Step | File | Description |
|------|------|-------------|
| 001  | `001-backend-operator-carrier-endpoints.md` | Add 4 CRUD endpoints to `operator.py` |
| 002  | `002-frontend-api-functions.md` | Add API functions + type to `operator.ts` |
| 003  | `003-frontend-operator-carriers-page.md` | Create `OperatorCarriersPage.tsx` component |
| 004  | `004-frontend-route-sidebar.md` | Wire route in `router.tsx` + sidebar entry in `AppSidebar.tsx` |
| 005  | `005-update-docs.md` | Update documentation for Phase 158 |

## Key Patterns

- **Backend:** `operator_connection(pool)` for RLS bypass, `log_operator_access()` for audit, `require_operator_admin` dependency on writes
- **Frontend page:** `SubscriptionsPage` — filters, table, tenant links, useQuery/useMutation
- **Frontend API:** `fetchDeviceSubscriptions` pattern — URLSearchParams builder
- **Sidebar:** `operatorTenantNav` array with `NavItem` shape
- **Router:** Operator children under `RequireOperator` guard

## Verification

```bash
# Backend route check
cd services/ui_iot && python -c "
from routes.operator import router
routes = [(r.path, r.methods) for r in router.routes]
carrier_routes = [r for r in routes if 'carrier' in r[0]]
print('Operator carrier routes:', carrier_routes)
assert len(carrier_routes) >= 3, 'Expected at least 3 carrier routes'
"

# Frontend build
cd frontend && npx tsc --noEmit && npm run build

# Manual: Log in as operator → sidebar shows "Carrier Integrations" under Tenants → /operator/carriers shows cross-tenant table
```
