# Prompt 005 — Nav Wiring + Routes

Read the operator router/nav file in `frontend/src/` — find where operator routes and nav links are defined.

## Add Routes

In the operator router (or `App.tsx`):
- `/operator/tenants` → TenantListPage
- `/operator/tenants/:tenantId` → TenantDetailPage
- `/operator/audit-log` → AuditLogPage

## Add Nav Links

In the operator sidebar/nav (find the existing operator nav component):
- "Tenants" → `/operator/tenants`
- "Audit Log" → `/operator/audit-log`

Place Tenants above Audit Log. Use existing nav item styling.

## Acceptance Criteria

- [ ] All three routes registered
- [ ] "Tenants" and "Audit Log" links in operator nav
- [ ] `npm run build` passes
