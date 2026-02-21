# Prompt 003 — Frontend: SitesPage

Read `frontend/src/features/devices/DeviceListPage.tsx` for layout/card patterns.
Read `frontend/src/services/api/devices.ts` for API client patterns.

## Create `frontend/src/features/sites/SitesPage.tsx`

A page showing all sites as cards. Each card displays:
- Site name and location
- Device count with breakdown: X online / Y stale / Z offline
- Active alert count (badge, red if > 0)
- Click → navigates to site detail (prompt 004)

## Add API Functions in `frontend/src/services/api/sites.ts` (new file)

```typescript
export interface SiteWithRollup {
  site_id: string;
  name: string;
  location: string | null;
  latitude: number | null;
  longitude: number | null;
  device_count: number;
  online_count: number;
  stale_count: number;
  offline_count: number;
  active_alert_count: number;
}

export async function fetchSites(): Promise<{ sites: SiteWithRollup[]; total: number }> {
  return apiFetch('/customer/sites');
}
```

## useSites Hook

Create `frontend/src/hooks/use-sites.ts`:

```typescript
export function useSites() {
  // fetch on mount, refetch every 30s
  // return { sites, total, isLoading, error, refetch }
}
```

## SiteCard Component

Each card:
- Name (bold, large)
- Location (subdued text, if set)
- Status row: green dot "X Online" | yellow dot "Y Stale" | red dot "Z Offline"
- Alert badge: "N Active Alerts" in red if > 0, green "No Active Alerts" if 0

## Acceptance Criteria

- [ ] SitesPage.tsx exists showing site cards
- [ ] Each card shows device status breakdown
- [ ] Alert badge shows active alert count
- [ ] `npm run build` passes
