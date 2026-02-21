# Prompt 003 — Nav + Route Wiring

Read `frontend/src/app/router.tsx` and `frontend/src/components/layout/AppSidebar.tsx`.

## Add Route

In the operator routes section of the router:
- `/operator/system-metrics` → SystemMetricsPage

## Add Nav Link

In the operator sidebar, add "System Metrics" link → `/operator/system-metrics`.
Place it near the top of the operator nav (after Dashboard / before Tenants).

## Acceptance Criteria

- [ ] `/operator/system-metrics` route registered
- [ ] "System Metrics" in operator nav
- [ ] `npm run build` passes
