# Prompt 004 — Frontend: Site Detail View + Navigation

Read `frontend/src/App.tsx` (or routing file) to understand route patterns.
Read `frontend/src/features/devices/DeviceListPage.tsx`.
Read `frontend/src/features/alerts/AlertListPage.tsx`.

## Create `frontend/src/features/sites/SiteDetailPage.tsx`

Route: `/sites/:siteId`

Page layout:
- Header: site name + location
- Two-column layout (or tabbed):
  - Left/Tab 1: Devices list (reuse DeviceListPage filtered to this site_id)
  - Right/Tab 2: Active Alerts list (reuse AlertListPage filtered to this site_id)
- Back button → /sites

Add API function in `sites.ts`:

```typescript
export interface SiteSummary {
  site: { site_id: string; name: string; location: string | null };
  devices: Array<{ device_id: string; name: string; status: string; device_type: string }>;
  active_alerts: Array<{ id: number; alert_type: string; severity: number; summary: string; status: string }>;
  device_count: number;
  active_alert_count: number;
}

export async function fetchSiteSummary(siteId: string): Promise<SiteSummary> {
  return apiFetch(`/customer/sites/${siteId}/summary`);
}
```

## Add Sites to Navigation

In the nav menu (find the existing nav component), add a "Sites" link pointing to `/sites`.
Place it between Dashboard and Devices in the nav order.

## Add Routes

In the router/App.tsx, add:
- `/sites` → SitesPage
- `/sites/:siteId` → SiteDetailPage

## Acceptance Criteria

- [ ] `/sites` route renders SitesPage
- [ ] `/sites/:siteId` route renders SiteDetailPage with device + alert lists
- [ ] "Sites" link in nav menu
- [ ] Back button from detail to list
- [ ] `npm run build` passes
