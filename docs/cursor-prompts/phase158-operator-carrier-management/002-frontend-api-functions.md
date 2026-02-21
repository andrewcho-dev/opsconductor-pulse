# Task 2: Frontend — Operator API Functions + Types

## File to Modify

`frontend/src/services/api/operator.ts`

## What to Do

Add the `OperatorCarrierIntegration` type and 4 API functions at the end of the file (after the existing account-tier functions). Follow the same patterns already used in this file — particularly the `fetchDeviceSubscriptions` URLSearchParams pattern and the `apiGet`/`apiPost`/`apiPatch`/`apiDelete` helpers from `./client`.

### Step 1: Add the type

Add after the existing `OperatorAccountTier` interface:

```typescript
export interface OperatorCarrierIntegration {
  id: number;
  tenant_id: string;
  carrier_name: string;
  display_name: string;
  enabled: boolean;
  account_id: string | null;
  api_key_masked: string | null;
  sync_enabled: boolean;
  sync_interval_minutes: number;
  last_sync_at: string | null;
  last_sync_status: string;
  last_sync_error: string | null;
  created_at: string;
}
```

### Step 2: Add the fetch function

```typescript
export async function fetchOperatorCarrierIntegrations(
  params?: { tenant_id?: string; carrier_name?: string; limit?: number; offset?: number }
): Promise<{ integrations: OperatorCarrierIntegration[]; total: number; limit: number; offset: number }> {
  const sp = new URLSearchParams();
  if (params?.tenant_id) sp.set("tenant_id", params.tenant_id);
  if (params?.carrier_name) sp.set("carrier_name", params.carrier_name);
  if (params?.limit) sp.set("limit", String(params.limit));
  if (params?.offset) sp.set("offset", String(params.offset));
  return apiGet(`/api/v1/operator/carrier-integrations${sp.toString() ? `?${sp.toString()}` : ""}`);
}
```

### Step 3: Add create function

```typescript
export async function createOperatorCarrierIntegration(data: {
  tenant_id: string;
  carrier_name: string;
  display_name: string;
  enabled?: boolean;
  api_key?: string | null;
  api_secret?: string | null;
  api_base_url?: string | null;
  account_id?: string | null;
  sync_enabled?: boolean;
  sync_interval_minutes?: number;
  config?: Record<string, unknown>;
}): Promise<OperatorCarrierIntegration> {
  return apiPost("/api/v1/operator/carrier-integrations", data);
}
```

### Step 4: Add update function

Note: the backend uses PUT, so use `apiPatch` or add an `apiPut` call. Check what's available in `./client`. If only `apiPatch` exists, the backend should accept both — but ideally match the HTTP method. If `apiPut` doesn't exist in `client.ts`, either add it (same pattern as `apiPatch` but with `method: "PUT"`) or just use `apiPatch` since the backend route uses `@router.put` which FastAPI will also handle. The safest approach: check `client.ts` for available methods. If there's no `apiPut`, create a simple wrapper or use the raw fetch:

```typescript
export async function updateOperatorCarrierIntegration(
  integrationId: number,
  data: {
    display_name?: string;
    enabled?: boolean;
    api_key?: string | null;
    api_secret?: string | null;
    api_base_url?: string | null;
    account_id?: string | null;
    sync_enabled?: boolean;
    sync_interval_minutes?: number;
    config?: Record<string, unknown>;
  }
): Promise<OperatorCarrierIntegration> {
  // Use apiPut if available in client.ts, otherwise use apiPatch
  // The backend endpoint is @router.put, so match accordingly
  return apiPatch(`/api/v1/operator/carrier-integrations/${integrationId}`, data);
}
```

**Important:** Check `frontend/src/services/api/client.ts` for available HTTP method helpers. The existing carrier customer routes in `carrier.py` use `@router.put` for updates. If there's an `apiPut` export, use that. If not, check how `update_carrier_integration` is called from the customer frontend — match that pattern.

### Step 5: Add delete function

```typescript
export async function deleteOperatorCarrierIntegration(integrationId: number): Promise<{ deleted: boolean; id: number }> {
  return apiDelete(`/api/v1/operator/carrier-integrations/${integrationId}`);
}
```

## Important Notes

- `apiGet`, `apiPost`, `apiPatch`, `apiDelete` are already imported at the top of this file from `./client`
- Follow the exact same patterns as the existing `fetchDeviceSubscriptions`, `createDeviceSubscription`, etc.
- The type fields match exactly what the backend returns (see Task 1 response shapes)
- `api_key_masked` (not `api_key`) — the backend never returns the raw key

## Verification

```bash
cd frontend && npx tsc --noEmit 2>&1 | head -20
```
