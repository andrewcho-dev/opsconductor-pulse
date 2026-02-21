# Prompt 003 — Frontend: Tenant Detail + Subscription Panel

## Create `frontend/src/features/operator/TenantDetailPage.tsx`

Route: `/operator/tenants/:tenantId`

Page sections:
1. **Tenant Info** — name, status, tenant_id, created_at. "Edit" button → inline edit or modal for PATCH /operator/tenants/{id}
2. **Stats card** — device_count, active_alert_count, subscription_count (from GET /operator/tenants/{id}/stats)
3. **Subscriptions panel** — list of tenant subscriptions, "Add Subscription" button
4. **Recent Devices** — first 10 devices for this tenant (GET /operator/tenants/{id}/devices)

## Subscription Panel

Sub-section within TenantDetailPage:

List columns: subscription_id, type, status, device_limit, term_end, description

"Add Subscription" button → opens inline form or modal:
- subscription_type: select (MAIN / ADDON / TRIAL / TEMPORARY)
- device_limit: number input (optional)
- term_end: date input (optional)
- description: text input

On submit: calls `createSubscription({ tenant_id, ...fields })`, refreshes list.

Edit button per subscription row → PATCH update (status, device_limit, term_end).

## Acceptance Criteria

- [ ] TenantDetailPage.tsx at /operator/tenants/:tenantId
- [ ] Shows tenant info, stats, subscriptions, devices
- [ ] Add Subscription form works
- [ ] Edit subscription inline or via modal
- [ ] `npm run build` passes
