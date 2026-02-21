# Phase 126: Customizable Dashboards

## Overview

Replace the current hardcoded `DashboardPage.tsx` with a fully customizable dashboard system. Users can create multiple dashboards, add/remove/configure widgets, and rearrange them via drag-and-drop. Dashboards can be personal (user-scoped) or shared (tenant-scoped). A default dashboard template is auto-created for new users.

**Depends on**: Phase 124 (UI Navigation Overhaul) -- assumes sidebar and router structure are stable.

## Tech Stack

- **Backend**: FastAPI + asyncpg + PostgreSQL (RLS with `tenant_connection`)
- **Frontend**: React 19 + TypeScript + Shadcn UI + Tailwind CSS 4 + TanStack React Query + ECharts + react-grid-layout (new dep)
- **Auth**: Keycloak JWT with `sub` claim for user_id, `organization` claim for tenant_id

## Execution Order

| Step | File | Description | Commit Message |
|------|------|-------------|----------------|
| 1 | `001-widget-system.md` | DB migration, backend CRUD API, frontend widget registry | `feat(dashboards): add dashboard/widget CRUD API and widget registry` |
| 2 | `002-drag-drop-layout.md` | react-grid-layout integration, DashboardBuilder, edit mode | `feat(dashboards): add drag-drop layout with react-grid-layout` |
| 3 | `003-personal-shared-dashboards.md` | Personal/shared ownership, default template, dashboard selector | `feat(dashboards): add personal/shared dashboards with default template` |

## Key Existing Files

### Backend
- `services/ui_iot/app.py` -- FastAPI app, router registration
- `services/ui_iot/routes/customer.py` -- Customer router (prefix `/customer`, JWT + RLS deps)
- `services/ui_iot/middleware/auth.py` -- `JWTBearer` dependency
- `services/ui_iot/middleware/tenant.py` -- `inject_tenant_context`, `get_tenant_id`, `get_user`, `require_customer`
- `services/ui_iot/db/pool.py` -- `tenant_connection(pool, tenant_id)` context manager (sets `SET LOCAL ROLE pulse_app` + `app.tenant_id`)
- `services/ui_iot/dependencies.py` -- `get_db_pool`, `pagination`
- `db/migrations/080_iam_permissions.sql` -- Latest migration (next = 081)

### Frontend
- `frontend/src/features/dashboard/DashboardPage.tsx` -- Current hardcoded dashboard (will be replaced)
- `frontend/src/features/dashboard/FleetKpiStrip.tsx` -- KPI strip component
- `frontend/src/features/dashboard/widgets/` -- Existing widgets: `StatCardsWidget`, `AlertStreamWidget`, `AlertTrendWidget`, `DeviceStatusWidget`, `DeviceTableWidget`, `FleetHealthWidget`
- `frontend/src/features/dashboard/widgets/index.ts` -- Widget barrel export
- `frontend/src/services/api/client.ts` -- `apiGet`, `apiPost`, `apiPut`, `apiDelete` helpers
- `frontend/src/services/auth/AuthProvider.tsx` -- `useAuth()` hook, provides `user.sub`, `user.tenantId`
- `frontend/src/app/router.tsx` -- React Router config, `{ path: "dashboard", element: <DashboardPage /> }`
- `frontend/src/components/layout/AppSidebar.tsx` -- Sidebar navigation
- `frontend/src/lib/charts/EChartWrapper.tsx` -- ECharts wrapper component
- `frontend/src/lib/charts/` -- Chart utilities (theme, colors, transforms, MetricGauge, TimeSeriesChart, UPlotChart)
- `frontend/src/components/ui/` -- Shadcn UI components (dialog, sheet, select, button, card, tabs, switch, label, dropdown-menu, etc.)
- `frontend/package.json` -- Has echarts, recharts, uplot; does NOT have react-grid-layout

## Architecture Decisions

1. **Dashboards table uses SERIAL PK** (not UUID) -- simpler for widget FK references and URL params
2. **Widget config stored as JSONB** -- each widget type has its own config schema, validated client-side
3. **Layout batch update endpoint** -- single PUT to save all widget positions after drag/drop (avoids N+1 updates)
4. **Widget registry pattern** -- maps `widget_type` string to React component, making it trivial to add new widget types later
5. **RLS on dashboards** -- tenant isolation at DB level; user_id filtering done in application queries
6. **Personal vs shared** -- `user_id = NULL` means shared; `user_id = '<sub>'` means personal

## Verification (after all 3 commits)

```bash
# 1. Backend: run migration
psql -U iot -d iotcloud -f db/migrations/081_dashboards.sql

# 2. Backend: verify tables exist
psql -U iot -d iotcloud -c "\d dashboards"
psql -U iot -d iotcloud -c "\d dashboard_widgets"

# 3. Frontend: verify no TypeScript errors
cd frontend && npx tsc --noEmit

# 4. Frontend: verify dev server starts
cd frontend && npm run dev

# 5. E2E flow: create dashboard, add widget, drag, reload, verify persistence
# (manual browser test or Playwright if available)
```
