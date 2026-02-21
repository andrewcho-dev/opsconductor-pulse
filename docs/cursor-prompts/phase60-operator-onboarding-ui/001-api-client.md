# Prompt 001 — API Client: Operator Functions

Read `frontend/src/services/api/` to understand the `apiFetch` pattern and any existing operator API functions.
Read `services/ui_iot/routes/operator.py` to understand exact request/response shapes.

## Create or Extend `frontend/src/services/api/operator.ts`

Add the following typed functions and interfaces:

```typescript
// ── Types ──────────────────────────────────────────────────────────────────

export interface Tenant {
  tenant_id: string;
  name: string;
  status: string;
  created_at: string;
}

export interface TenantStats {
  tenant_id: string;
  device_count: number;
  active_alert_count: number;
  subscription_count: number;
  // include whatever fields the API returns
}

export interface Subscription {
  subscription_id: string;
  tenant_id: string;
  subscription_type: string; // MAIN | ADDON | TRIAL | TEMPORARY
  status: string;
  device_limit: number | null;
  term_end: string | null;
  description: string | null;
  created_at: string;
}

export interface AuditEvent {
  id: string | number;
  tenant_id: string;
  category: string;
  severity: string;
  entity_type: string;
  entity_id: string;
  message: string;
  created_at: string;
}

// ── Tenant Functions ────────────────────────────────────────────────────────

export async function fetchOperatorTenants(params?: {
  status?: string; limit?: number; offset?: number;
}): Promise<{ tenants: Tenant[]; total: number }> {
  const qs = new URLSearchParams(params as any).toString();
  return apiFetch(`/operator/tenants${qs ? '?' + qs : ''}`);
}

export async function fetchTenantDetail(tenantId: string): Promise<Tenant> {
  return apiFetch(`/operator/tenants/${tenantId}`);
}

export async function fetchTenantStats(tenantId: string): Promise<TenantStats> {
  return apiFetch(`/operator/tenants/${tenantId}/stats`);
}

export async function createTenant(data: { name: string; [key: string]: any }): Promise<Tenant> {
  return apiFetch('/operator/tenants', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
}

export async function updateTenant(tenantId: string, data: Partial<Tenant>): Promise<Tenant> {
  return apiFetch(`/operator/tenants/${tenantId}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
}

// ── Subscription Functions ──────────────────────────────────────────────────

export async function fetchSubscriptions(params?: {
  tenant_id?: string; status?: string; limit?: number;
}): Promise<{ subscriptions: Subscription[] }> {
  const qs = new URLSearchParams(params as any).toString();
  return apiFetch(`/operator/subscriptions${qs ? '?' + qs : ''}`);
}

export async function createSubscription(data: {
  tenant_id: string;
  subscription_type: string;
  device_limit?: number;
  term_end?: string;
  description?: string;
}): Promise<Subscription> {
  return apiFetch('/operator/subscriptions', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
}

export async function updateSubscription(
  subscriptionId: string,
  data: Partial<Subscription>
): Promise<Subscription> {
  return apiFetch(`/operator/subscriptions/${subscriptionId}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
}

// ── Audit Log ───────────────────────────────────────────────────────────────

export async function fetchAuditLog(params?: {
  tenant_id?: string; category?: string; severity?: string;
  entity_type?: string; limit?: number; offset?: number;
}): Promise<{ events: AuditEvent[]; total: number }> {
  const qs = new URLSearchParams(params as any).toString();
  return apiFetch(`/operator/audit-log${qs ? '?' + qs : ''}`);
}
```

## Acceptance Criteria

- [ ] All functions and types defined
- [ ] `npm run build` passes (TypeScript clean)
