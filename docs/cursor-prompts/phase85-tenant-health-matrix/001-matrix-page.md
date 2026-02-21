# Prompt 001 — TenantHealthMatrix Page

Read `frontend/src/features/operator/TenantListPage.tsx` and
`frontend/src/services/api/operator.ts` to understand existing data structures.

## Create `frontend/src/features/operator/TenantHealthMatrix.tsx`

A full-page dense health matrix for all tenants.

### Page layout:
```
┌─────────────────────────────────────────────────────────────────┐
│  Tenant Health Matrix    [Search___] [Sort: Alerts▾] [↻ 30s]   │
├────────────┬────────┬──────────────┬────────────┬──────────────┤
│ TENANT     │DEVICES │ DEVICE HEALTH│ ALERTS     │ LAST ACTIVE  │
│            │        │ (bar)        │            │              │
├────────────┼────────┼──────────────┼────────────┼──────────────┤
│ acme-corp  │ 24/30  │ ████░░ 80%   │ ⚠ 3 open   │ 2m ago       │
│ beta-inc   │ 12/12  │ ██████ 100%  │ ✓ none     │ 5m ago       │
│ gamma-llc  │  0/5   │ ░░░░░░  0%  │ ● 12 open  │ 2h ago       │
└────────────┴────────┴──────────────┴────────────┴──────────────┘
```

### Columns:
1. **Tenant** — tenant_id (bold), subscription plan badge (small)
2. **Devices** — "online/total" format
3. **Device Health** — colored progress bar (green ≥90%, yellow ≥70%, red <70%)
4. **Alerts** — count with color: 0=gray checkmark, 1-5=yellow warning, >5=red circle
5. **Last Active** — time since last telemetry (relative, e.g., "3m ago")
6. **Status** — subscription status badge (ACTIVE/EXPIRED/SUSPENDED)

### Data fetching:
```typescript
const { data: tenantsData } = useQuery({
  queryKey: ['operator-tenants-health'],
  queryFn: () => apiGet('/operator/tenants?limit=100'),
  refetchInterval: 30000,
});
```

Each tenant row from the list should include:
- `device_count` (total registered)
- `online_device_count` (or compute from stats)
- `open_alert_count`
- `last_telemetry_at` or `last_active_at`
- `subscription_status`

If the tenant list endpoint doesn't return all these fields, fetch
GET /operator/system/aggregates which has per-tenant breakdowns, or
use GET /operator/tenants/{id}/stats for each tenant (limit to visible rows only).

### Sort options:
- By Alerts (descending) — default
- By Devices (descending)  
- By Last Active (most recent first)
- By Tenant Name (A-Z)

### Search:
Client-side filter on tenant_id/name.

### Row click:
Navigate to `/operator/tenants/{tenant_id}`.

### Row health color coding:
- Row background: subtle red tint if open_alerts > 5
- Row background: subtle yellow tint if online_pct < 70%
- Default: transparent

### Auto-refresh indicator:
Top-right: spinning icon when fetching, "↻ 30s" countdown.

## Wire route + nav:
In `router.tsx`: add `{ path: 'tenant-matrix', element: <TenantHealthMatrix /> }` under operator.
In `AppSidebar.tsx`: add "Health Matrix" link under Tenants group, icon: `LayoutGrid`.

## Acceptance Criteria
- [ ] TenantHealthMatrix.tsx renders all tenants in dense table
- [ ] Device health bar colored by online %
- [ ] Alert count colored by severity
- [ ] Sort by Alerts/Devices/LastActive/Name
- [ ] Search/filter by tenant name
- [ ] Row click navigates to TenantDetailPage
- [ ] Route /operator/tenant-matrix wired
- [ ] Nav link added
- [ ] `npm run build` passes
