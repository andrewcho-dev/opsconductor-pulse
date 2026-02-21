# Prompt 003 — Frontend: Update API Client + Hook

## Context

The backend now accepts filter params and returns `total`. The frontend API client and React Query hook must be updated to pass these params and consume the new response shape.

## Your Task

### Step 1: Update `frontend/src/services/api/devices.ts`

Update `fetchDevices()`:

```typescript
export interface DeviceListParams {
  limit?: number;
  offset?: number;
  status?: string;     // "ONLINE" | "STALE" | "OFFLINE"
  tags?: string[];     // will be joined as comma-separated
  q?: string;          // search query
  site_id?: string;
}

export async function fetchDevices(
  params: DeviceListParams = {}
): Promise<DeviceListResponse> {
  const { limit = 100, offset = 0, status, tags, q, site_id } = params;
  const searchParams = new URLSearchParams();
  searchParams.set("limit", String(limit));
  searchParams.set("offset", String(offset));
  if (status) searchParams.set("status", status);
  if (tags && tags.length > 0) searchParams.set("tags", tags.join(","));
  if (q) searchParams.set("q", q);
  if (site_id) searchParams.set("site_id", site_id);

  return apiGet(`/api/v2/devices?${searchParams.toString()}`);
}

export async function fetchFleetSummary(): Promise<FleetSummary> {
  return apiGet("/customer/devices/summary");
}
```

Add `FleetSummary` type:
```typescript
export interface FleetSummary {
  ONLINE: number;
  STALE: number;
  OFFLINE: number;
  total: number;
}
```

Update `DeviceListResponse` to include `total`:
```typescript
export interface DeviceListResponse {
  tenant_id: string;
  devices: Device[];
  total: number;
  limit: number;
  offset: number;
}
```

### Step 2: Update `frontend/src/hooks/use-devices.ts`

Update `useDevices()` to accept filter params:

```typescript
export function useDevices(params: DeviceListParams = {}) {
  return useQuery({
    queryKey: ["devices", params],  // params object in key — refetches on any change
    queryFn: () => fetchDevices(params),
  });
}

export function useFleetSummary() {
  return useQuery({
    queryKey: ["fleet-summary"],
    queryFn: fetchFleetSummary,
    refetchInterval: 30_000,  // refresh every 30s
  });
}
```

Import `DeviceListParams` and `fetchFleetSummary` from the API client.

### Step 3: Update `DeviceListPage.tsx`

Remove the client-side tag filtering logic (the `filteredDevices` useMemo). Replace with server-side:

- Move `selectedTags`, `status`, `q`, `site_id` into a `filters` state object
- Pass filters directly to `useDevices(filters)`
- Remove the `getAllTags()` call that was used only for client-side filtering — tags will still be fetched for the filter UI (keep that)
- The `total` from the response drives the pagination "X of N" display

**Important:** When any filter changes, reset `offset` to `0`.

## Acceptance Criteria

- [ ] `fetchDevices()` accepts `DeviceListParams` and builds correct query string
- [ ] `fetchFleetSummary()` calls `/customer/devices/summary`
- [ ] `useDevices(params)` includes full params in query key
- [ ] `useFleetSummary()` exists with 30s refresh
- [ ] `DeviceListResponse` includes `total: number`
- [ ] Client-side `filteredDevices` useMemo removed from `DeviceListPage.tsx`
- [ ] Filter changes reset offset to 0
- [ ] `pytest -m unit -v` passes (no backend changes in this prompt)
- [ ] `npm run build` clean
