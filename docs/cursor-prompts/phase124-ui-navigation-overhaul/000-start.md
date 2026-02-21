# Phase 124: UI Navigation Overhaul

## Depends On
- Phase 119 (UI Foundation -- toast system, forms, tables, 404 catch-all)

## Goal
Improve the navigation and discoverability experience across OpsConductor Pulse: global Cmd+K search, cleaned-up sidebar, new-tenant onboarding checklist, and user profile/preferences page with backend persistence.

## Tech Stack
- React 19 + TypeScript
- Shadcn UI + Tailwind CSS 4
- TanStack React Query v5
- React Router v7 (react-router-dom ^7.13)
- Keycloak auth (keycloak-js ^26.2)
- Backend: FastAPI + asyncpg + PostgreSQL (RLS via `tenant_connection`)
- `cmdk` package (to be installed in task 001)

## Execution Order

| # | File | Description | Commit message |
|---|------|-------------|----------------|
| 1 | `001-global-search-cmd-k.md` | Install cmdk, create Command component + CommandPalette, mount in AppShell | `feat(ui): add Cmd+K global search command palette` |
| 2 | `002-sidebar-consolidation.md` | Restructure sidebar nav groups, fix broken links, remove dead items | `refactor(ui): consolidate sidebar nav groups and fix broken links` |
| 3 | `003-onboarding-flow.md` | Create onboarding checklist for new tenants on DashboardPage | `feat(ui): add new-tenant onboarding checklist on dashboard` |
| 4 | `004-user-profile-preferences.md` | DB migration + backend route + frontend ProfilePage at /settings/profile | `feat: add user profile preferences page with timezone support` |

## Key Files (existing, read-only context)

| File | Purpose |
|------|---------|
| `frontend/src/components/layout/AppShell.tsx` | Main layout shell -- SidebarProvider, AppSidebar, AppHeader, Outlet |
| `frontend/src/components/layout/AppSidebar.tsx` | 446-line sidebar with role-based nav groups, localStorage collapsible state |
| `frontend/src/components/layout/AppHeader.tsx` | Top bar with theme toggle, connection status, tenant badge, logout |
| `frontend/src/app/router.tsx` | React Router v7 config with RequireCustomer/RequireOperator guards, basename `/app` |
| `frontend/src/features/dashboard/DashboardPage.tsx` | Dashboard page with FleetKpiStrip, alerts, device widgets |
| `frontend/src/services/api/client.ts` | `apiGet`, `apiPost`, `apiPut`, `apiPatch`, `apiDelete` with Keycloak token refresh |
| `frontend/src/services/api/devices.ts` | `fetchDevices(params)` with search/q params, `fetchDevice(id)` |
| `frontend/src/services/api/alerts.ts` | `fetchAlerts(status, limit, offset, alertType)` |
| `frontend/src/services/api/users.ts` | `fetchTenantUsers(search)`, `fetchOperatorUsers(search, tenantFilter)` |
| `frontend/src/services/api/types.ts` | All shared TypeScript interfaces (Device, Alert, DeviceListResponse, etc.) |
| `frontend/src/services/auth/AuthProvider.tsx` | `useAuth()` context: `{ user, isCustomer, isOperator, logout }` |
| `frontend/src/hooks/use-devices.ts` | `useDevices(params)`, `useDevice(id)`, `useFleetSummary()` |
| `frontend/src/hooks/use-alerts.ts` | TanStack Query hook wrapping `fetchAlerts` |
| `frontend/src/components/shared/` | PageHeader, EmptyState, StatusBadge, SeverityBadge, ErrorMessage, etc. |
| `frontend/package.json` | Dependencies -- does NOT have cmdk yet |
| `services/ui_iot/app.py` | FastAPI app, includes all routers, startup/shutdown lifecycle |
| `services/ui_iot/routes/roles.py` | Example of customer route pattern with `JWTBearer`, `tenant_connection`, audit |
| `services/ui_iot/middleware/tenant.py` | `inject_tenant_context`, `require_customer`, `get_tenant_id`, `get_user` |
| `services/ui_iot/db/pool.py` | `tenant_connection(pool, tenant_id)`, `operator_connection(pool)` |
| `db/migrations/080_iam_permissions.sql` | Latest migration -- IAM permissions system |

## Verification (after all 4 tasks)

1. **Cmd+K palette**: Press Cmd+K (Mac) or Ctrl+K (Windows) anywhere in the app. Type a device ID -- results appear grouped by category. Select a device -- navigates to `/devices/{id}`. Type a page name like "alerts" -- shows page navigation option.
2. **Sidebar**: All links resolve to valid routes. No "Export" or "Notification Prefs" dead links. Groups are: Overview, Fleet, Monitoring, Notifications, Analytics, Settings. Operator nav unchanged.
3. **Onboarding**: Log in as a new tenant with 0 devices. Dashboard shows checklist card above FleetKpiStrip. Complete steps, checklist updates. Dismiss persists across page loads.
4. **Profile**: Navigate to Settings > Profile in sidebar. Set timezone, display name. Save -- toast confirms. Reload page -- values persist from backend. Email field is read-only.
5. **Build**: `cd frontend && npm run build` succeeds with zero TypeScript errors.
6. **Tests**: `cd frontend && npm test` passes.
