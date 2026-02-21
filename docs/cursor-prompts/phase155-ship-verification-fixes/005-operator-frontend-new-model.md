# Task 005 — Rewrite Operator Subscription/Tier UI for Phase 156 Model

## Problem

Phase 156 replaced the subscription and device tier backend with a new model:

- **Old:** `subscriptions` table (per-tenant, type MAIN/ADDON/TRIAL/TEMPORARY, with device_limit) + `device_tiers` table (feature flags only)
- **New:** `device_subscriptions` table (per-device, 1:1 device mapping, with plan_id) + `device_plans` table (limits + features + pricing) + `account_tiers` table (tenant-level shared resources + pricing)

The old operator endpoints now return **410 Gone**:
- `GET /api/v1/operator/subscriptions` → 410
- `POST /api/v1/operator/subscriptions` → 410
- `PATCH /api/v1/operator/subscriptions/{id}` → 410
- `GET /api/v1/operator/subscriptions/{id}` → 410
- `GET /api/v1/operator/subscriptions/expiring-notifications` → 410
- `GET /api/v1/operator/device-tiers` → 410
- `POST /api/v1/operator/device-tiers` → 410
- `PUT /api/v1/operator/device-tiers/{id}` → 410

The new endpoints are:
- `GET /api/v1/operator/device-subscriptions` (filters: tenant_id, device_id, status)
- `POST /api/v1/operator/device-subscriptions` (body: tenant_id, device_id, plan_id, status?, term_start?, term_end?)
- `PATCH /api/v1/operator/device-subscriptions/{subscription_id}` (body: plan_id?, status?, term_end?)
- `DELETE /api/v1/operator/device-subscriptions/{subscription_id}` (cancels it)
- `GET /api/v1/operator/device-plans`
- `POST /api/v1/operator/device-plans` (body: plan_id, name, description, limits, features, monthly_price_cents, annual_price_cents, sort_order)
- `PUT /api/v1/operator/device-plans/{plan_id}` (body: name?, description?, limits?, features?, monthly_price_cents?, annual_price_cents?, sort_order?, is_active?)
- `DELETE /api/v1/operator/device-plans/{plan_id}` (deactivates)
- `GET /api/v1/operator/account-tiers`
- `POST /api/v1/operator/account-tiers` (body: tier_id, name, description, limits, features, support, monthly_price_cents, annual_price_cents, sort_order)
- `PUT /api/v1/operator/account-tiers/{tier_id}` (body: name?, description?, limits?, features?, support?, monthly_price_cents?, annual_price_cents?, sort_order?, is_active?)
- `DELETE /api/v1/operator/account-tiers/{tier_id}` (deactivates)
- `PATCH /api/v1/operator/tenants/{tenant_id}/tier` (body: tier_id)

## Files to Modify

**API layer:**
1. `frontend/src/services/api/operator.ts` — Replace subscription functions
2. `frontend/src/services/api/device-tiers.ts` — Replace with device-plans API
3. `frontend/src/services/api/types.ts` — Update `SubscriptionDetail` type

**Pages/Components:**
4. `frontend/src/features/operator/SubscriptionsPage.tsx` — Rewrite for device subscriptions
5. `frontend/src/features/operator/SubscriptionDetailPage.tsx` — Rewrite for single device subscription
6. `frontend/src/features/operator/DeviceTiersPage.tsx` — Rewrite as device plans manager
7. `frontend/src/features/operator/CreateSubscriptionDialog.tsx` — Rewrite for device subscription creation
8. `frontend/src/features/operator/EditSubscriptionDialog.tsx` — Rewrite for device subscription editing
9. `frontend/src/features/operator/StatusChangeDialog.tsx` — Update endpoint path
10. `frontend/src/features/operator/SubscriptionInfoCards.tsx` — Update for device subscription shape
11. `frontend/src/features/operator/SubscriptionDeviceList.tsx` — Simplify (1 device per subscription)
12. `frontend/src/features/operator/OperatorTenantDetailPage.tsx` — Update subscription section
13. `frontend/src/features/operator/BulkAssignDialog.tsx` — Remove or rewrite
14. `frontend/src/features/operator/DeviceSubscriptionDialog.tsx` — Update endpoint path

**Navigation/Routing:**
15. `frontend/src/components/layout/AppSidebar.tsx` — Update sidebar labels
16. `frontend/src/app/router.tsx` — Update route paths and add account-tiers route

---

## Part 1: API Layer

### 1a. Update `operator.ts`

**Remove** the old `Subscription` interface and subscription API functions. **Replace** with:

```typescript
// ─── Device Subscriptions (Phase 156) ───────────────────

export interface DeviceSubscriptionRow {
  subscription_id: string;
  tenant_id: string;
  device_id: string;
  plan_id: string;
  status: "TRIAL" | "ACTIVE" | "GRACE" | "SUSPENDED" | "EXPIRED" | "CANCELLED";
  term_start: string;
  term_end: string | null;
  grace_end: string | null;
  stripe_subscription_id: string | null;
  created_at: string;
  updated_at: string;
}

export async function fetchDeviceSubscriptions(params?: {
  tenant_id?: string;
  device_id?: string;
  status?: string;
}): Promise<{ subscriptions: DeviceSubscriptionRow[] }> {
  const sp = new URLSearchParams();
  if (params?.tenant_id) sp.set("tenant_id", params.tenant_id);
  if (params?.device_id) sp.set("device_id", params.device_id);
  if (params?.status) sp.set("status", params.status);
  return apiGet(`/api/v1/operator/device-subscriptions${sp.toString() ? `?${sp.toString()}` : ""}`);
}

export async function createDeviceSubscription(data: {
  tenant_id: string;
  device_id: string;
  plan_id: string;
  status?: string;
  term_start?: string;
  term_end?: string;
}): Promise<DeviceSubscriptionRow> {
  return apiPost("/api/v1/operator/device-subscriptions", data);
}

export async function updateDeviceSubscription(
  subscriptionId: string,
  data: {
    plan_id?: string;
    status?: string;
    term_end?: string;
  }
): Promise<DeviceSubscriptionRow> {
  return apiPatch(`/api/v1/operator/device-subscriptions/${encodeURIComponent(subscriptionId)}`, data);
}

export async function cancelDeviceSubscription(
  subscriptionId: string
): Promise<DeviceSubscriptionRow> {
  return apiDelete(`/api/v1/operator/device-subscriptions/${encodeURIComponent(subscriptionId)}`);
}

// ─── Account Tiers (Phase 156) ──────────────────────────

export interface OperatorAccountTier {
  tier_id: string;
  name: string;
  description: string;
  limits: Record<string, number>;
  features: Record<string, boolean>;
  support: Record<string, unknown>;
  monthly_price_cents: number;
  annual_price_cents: number;
  sort_order: number;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export async function fetchAccountTiers(): Promise<{ tiers: OperatorAccountTier[] }> {
  return apiGet("/api/v1/operator/account-tiers");
}

export async function assignTenantTier(tenantId: string, tierId: string): Promise<void> {
  return apiPatch(`/api/v1/operator/tenants/${encodeURIComponent(tenantId)}/tier`, { tier_id: tierId });
}
```

Also **remove** the old `ExpiryNotification` interface and `fetchExpiryNotifications` function (there is no equivalent in the new model — expiry notifications were a legacy feature).

Remove the old `Subscription` interface (lines ~248–257), `fetchSubscriptions` (lines ~328–338), `createSubscription` (lines ~340–348), `updateSubscription` (lines ~350–355), `ExpiryNotification` interface (lines ~259–268), and `fetchExpiryNotifications` (lines ~270–284).

### 1b. Rewrite `device-tiers.ts` → device plans

Replace the entire file content:

```typescript
import { apiGet, apiPost, apiPut, apiDelete } from "./client";

export interface OperatorDevicePlan {
  plan_id: string;
  name: string;
  description: string;
  limits: Record<string, number>;
  features: Record<string, boolean>;
  monthly_price_cents: number;
  annual_price_cents: number;
  sort_order: number;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export async function fetchDevicePlans(): Promise<{ plans: OperatorDevicePlan[] }> {
  return apiGet("/api/v1/operator/device-plans");
}

export async function createDevicePlan(data: {
  plan_id: string;
  name: string;
  description?: string;
  limits: Record<string, number>;
  features: Record<string, boolean>;
  monthly_price_cents: number;
  annual_price_cents: number;
  sort_order: number;
}): Promise<OperatorDevicePlan> {
  return apiPost("/api/v1/operator/device-plans", data);
}

export async function updateDevicePlan(
  planId: string,
  data: {
    name?: string;
    description?: string;
    limits?: Record<string, number>;
    features?: Record<string, boolean>;
    monthly_price_cents?: number;
    annual_price_cents?: number;
    sort_order?: number;
    is_active?: boolean;
  }
): Promise<OperatorDevicePlan> {
  return apiPut(`/api/v1/operator/device-plans/${encodeURIComponent(planId)}`, data);
}

export async function deactivateDevicePlan(planId: string): Promise<OperatorDevicePlan> {
  return apiDelete(`/api/v1/operator/device-plans/${encodeURIComponent(planId)}`);
}
```

**Important:** Update ALL imports throughout the codebase that reference the old exports:
- `OperatorDeviceTier` → `OperatorDevicePlan`
- `fetchDeviceTiers` → `fetchDevicePlans`
- `createDeviceTier` → `createDevicePlan`
- `updateDeviceTier` → `updateDevicePlan`

### 1c. Update `types.ts`

Replace the `SubscriptionDetail` interface (around line 374). The old model had parent/child subscriptions and a devices array. The new model is 1 subscription = 1 device:

```typescript
export interface SubscriptionDetail {
  subscription_id: string;
  tenant_id: string;
  device_id: string;
  plan_id: string;
  status: "TRIAL" | "ACTIVE" | "GRACE" | "SUSPENDED" | "EXPIRED" | "CANCELLED";
  term_start: string;
  term_end: string | null;
  grace_end: string | null;
  stripe_subscription_id: string | null;
  created_at: string;
  updated_at: string;
}
```

Remove `SubscriptionDevice` and `ChildSubscription` interfaces if they only serve the old `SubscriptionDetail`. Search for other usages first.

---

## Part 2: Rewrite SubscriptionsPage.tsx → Device Subscriptions List

Replace the entire page. The new model lists per-device subscriptions.

Key differences:
- No more `subscription_type` (MAIN/ADDON/TRIAL/TEMPORARY) — all subscriptions are per-device
- No more `device_limit` / `active_device_count` — each subscription covers exactly 1 device
- Columns: Subscription ID, Tenant ID, Device ID, Plan, Status, Term End
- Filters: status, tenant_id (text input)

```tsx
"use client";

import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { format } from "date-fns";
import { PageHeader, StatusBadge } from "@/components/shared";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from "@/components/ui/table";
import {
  fetchDeviceSubscriptions,
  type DeviceSubscriptionRow,
} from "@/services/api/operator";

const STATUS_OPTIONS = ["ALL", "TRIAL", "ACTIVE", "GRACE", "SUSPENDED", "EXPIRED", "CANCELLED"] as const;

export default function SubscriptionsPage() {
  const [statusFilter, setStatusFilter] = useState<(typeof STATUS_OPTIONS)[number]>("ALL");
  const [tenantFilter, setTenantFilter] = useState("");

  const params = useMemo(() => {
    const p: Record<string, string> = {};
    if (statusFilter !== "ALL") p.status = statusFilter;
    if (tenantFilter.trim()) p.tenant_id = tenantFilter.trim();
    return p;
  }, [statusFilter, tenantFilter]);

  const { data, isLoading } = useQuery({
    queryKey: ["operator-device-subscriptions", params],
    queryFn: () => fetchDeviceSubscriptions(params),
  });

  const rows = data?.subscriptions ?? [];

  return (
    <div className="space-y-4">
      <PageHeader
        title="Device Subscriptions"
        description="Manage per-device subscriptions across all tenants"
      />

      <div className="flex flex-wrap items-center gap-3">
        <div className="w-44">
          <Select value={statusFilter} onValueChange={(v) => setStatusFilter(v as typeof statusFilter)}>
            <SelectTrigger><SelectValue placeholder="Status" /></SelectTrigger>
            <SelectContent>
              {STATUS_OPTIONS.map((s) => (
                <SelectItem key={s} value={s}>{s}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <Input
          className="w-56"
          placeholder="Filter by tenant ID"
          value={tenantFilter}
          onChange={(e) => setTenantFilter(e.target.value)}
        />
      </div>

      <div className="rounded-md border">
        <Table aria-label="Device subscriptions list">
          <TableHeader>
            <TableRow>
              <TableHead>Subscription ID</TableHead>
              <TableHead>Tenant</TableHead>
              <TableHead>Device</TableHead>
              <TableHead>Plan</TableHead>
              <TableHead>Term End</TableHead>
              <TableHead>Status</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {isLoading && (
              <TableRow>
                <TableCell colSpan={6} className="text-sm text-muted-foreground">
                  Loading subscriptions...
                </TableCell>
              </TableRow>
            )}
            {!isLoading && rows.length === 0 && (
              <TableRow>
                <TableCell colSpan={6} className="text-sm text-muted-foreground">
                  No device subscriptions found.
                </TableCell>
              </TableRow>
            )}
            {rows.map((row) => (
              <TableRow key={row.subscription_id}>
                <TableCell className="font-mono text-sm">
                  {row.subscription_id}
                </TableCell>
                <TableCell>
                  <Link className="text-primary hover:underline" to={`/operator/tenants/${row.tenant_id}`}>
                    {row.tenant_id}
                  </Link>
                </TableCell>
                <TableCell className="font-mono text-sm">{row.device_id}</TableCell>
                <TableCell>
                  <Badge variant="outline">{row.plan_id}</Badge>
                </TableCell>
                <TableCell>
                  {row.term_end ? format(new Date(row.term_end), "MMM d, yyyy") : "—"}
                </TableCell>
                <TableCell>
                  <StatusBadge status={row.status} variant="subscription" />
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
    </div>
  );
}
```

**Note:** Remove the `CreateSubscriptionDialog` import and button from this page. Creating device subscriptions is typically done from the tenant detail page (where you know the tenant_id and can select a device).

---

## Part 3: Rewrite SubscriptionDetailPage.tsx

The detail page no longer fetches from `/operator/subscriptions/{id}`. Since the new `GET /operator/device-subscriptions` endpoint doesn't have a single-item variant, fetch the list filtered by subscription_id is not possible by ID directly.

**Simplest approach:** Remove the subscription detail page route entirely. The list page has all the info needed (subscription_id, device_id, plan_id, status, term). If you need a detail view, do a client-side filter.

**Alternative:** Keep a simplified detail page that fetches from the list and filters client-side:

Replace the page with a simplified version that uses `fetchDeviceSubscriptions()` and finds the matching row. Remove:
- All references to `parent_subscription_id` and `child_subscriptions` (don't exist in new model)
- `SubscriptionDeviceList` (each subscription IS for one device)
- `SubscriptionInfoCards` (simplify — show device, plan, status, term dates)
- `EditSubscriptionDialog` (replace with inline status/plan change via `updateDeviceSubscription`)

```tsx
"use client";

import { useState } from "react";
import { Link, useParams, useNavigate } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { format, formatDistanceToNow } from "date-fns";
import { PageHeader, StatusBadge } from "@/components/shared";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";
import { Cpu, Calendar, Building2, CreditCard } from "lucide-react";
import { toast } from "sonner";
import {
  fetchDeviceSubscriptions,
  updateDeviceSubscription,
  cancelDeviceSubscription,
  fetchDevicePlans,
} from "@/services/api/operator";

// NOTE: Import fetchDevicePlans from operator.ts (add if needed) or from device-tiers.ts (renamed).
// If fetchDevicePlans is in device-tiers.ts (now the device-plans API file), import from there:
// import { fetchDevicePlans } from "@/services/api/device-tiers";

export default function SubscriptionDetailPage() {
  const { subscriptionId } = useParams<{ subscriptionId: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [newStatus, setNewStatus] = useState<string>("");
  const [newPlanId, setNewPlanId] = useState<string>("");

  const { data: subsData, isLoading } = useQuery({
    queryKey: ["operator-device-subscriptions"],
    queryFn: () => fetchDeviceSubscriptions(),
  });

  const { data: plansData } = useQuery({
    queryKey: ["operator-device-plans"],
    queryFn: () => fetchDevicePlans(),
  });

  const sub = subsData?.subscriptions?.find((s) => s.subscription_id === subscriptionId);
  const plans = plansData?.plans ?? [];

  const statusMutation = useMutation({
    mutationFn: (status: string) => updateDeviceSubscription(subscriptionId!, { status }),
    onSuccess: () => {
      toast.success("Status updated");
      queryClient.invalidateQueries({ queryKey: ["operator-device-subscriptions"] });
    },
    onError: (err: Error) => toast.error(err.message || "Failed to update status"),
  });

  const planMutation = useMutation({
    mutationFn: (plan_id: string) => updateDeviceSubscription(subscriptionId!, { plan_id }),
    onSuccess: () => {
      toast.success("Plan updated");
      queryClient.invalidateQueries({ queryKey: ["operator-device-subscriptions"] });
    },
    onError: (err: Error) => toast.error(err.message || "Failed to update plan"),
  });

  const cancelMutation = useMutation({
    mutationFn: () => cancelDeviceSubscription(subscriptionId!),
    onSuccess: () => {
      toast.success("Subscription cancelled");
      navigate("/operator/subscriptions");
    },
    onError: (err: Error) => toast.error(err.message || "Failed to cancel"),
  });

  if (isLoading) return <div>Loading...</div>;
  if (!sub) return <div>Subscription not found</div>;

  const STATUS_OPTIONS = ["TRIAL", "ACTIVE", "GRACE", "SUSPENDED", "EXPIRED", "CANCELLED"];

  return (
    <div className="space-y-4">
      <PageHeader
        title={sub.subscription_id}
        description={`Device subscription for ${sub.device_id}`}
        breadcrumbs={[
          { label: "Subscriptions", href: "/operator/subscriptions" },
          { label: sub.subscription_id },
        ]}
      />

      <div className="flex items-center gap-3">
        <StatusBadge status={sub.status} variant="subscription" />
        <Badge variant="outline">{sub.plan_id}</Badge>
      </div>

      <div className="grid gap-3 md:grid-cols-4">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="flex items-center gap-2 text-sm"><Cpu className="h-4 w-4" />Device</CardTitle>
          </CardHeader>
          <CardContent>
            <span className="font-mono text-sm">{sub.device_id}</span>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="flex items-center gap-2 text-sm"><CreditCard className="h-4 w-4" />Plan</CardTitle>
          </CardHeader>
          <CardContent>
            <Badge variant="outline">{sub.plan_id}</Badge>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="flex items-center gap-2 text-sm"><Calendar className="h-4 w-4" />Term</CardTitle>
          </CardHeader>
          <CardContent className="text-sm">
            <div>{sub.term_start ? format(new Date(sub.term_start), "MMM d, yyyy") : "—"}</div>
            <div>{sub.term_end ? format(new Date(sub.term_end), "MMM d, yyyy") : "Open-ended"}</div>
            {sub.term_end && new Date(sub.term_end) > new Date() && (
              <div className="text-xs text-muted-foreground mt-1">
                Expires {formatDistanceToNow(new Date(sub.term_end), { addSuffix: true })}
              </div>
            )}
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="flex items-center gap-2 text-sm"><Building2 className="h-4 w-4" />Tenant</CardTitle>
          </CardHeader>
          <CardContent>
            <Link to={`/operator/tenants/${sub.tenant_id}`} className="text-primary hover:underline text-sm">
              {sub.tenant_id}
            </Link>
          </CardContent>
        </Card>
      </div>

      {/* Status change */}
      <Card>
        <CardHeader><CardTitle className="text-sm">Change Status</CardTitle></CardHeader>
        <CardContent className="flex items-center gap-3">
          <Select value={newStatus || sub.status} onValueChange={setNewStatus}>
            <SelectTrigger className="w-48"><SelectValue /></SelectTrigger>
            <SelectContent>
              {STATUS_OPTIONS.map((s) => <SelectItem key={s} value={s}>{s}</SelectItem>)}
            </SelectContent>
          </Select>
          <Button
            size="sm"
            onClick={() => statusMutation.mutate(newStatus)}
            disabled={!newStatus || newStatus === sub.status || statusMutation.isPending}
          >
            {statusMutation.isPending ? "Updating..." : "Update Status"}
          </Button>
        </CardContent>
      </Card>

      {/* Plan change */}
      <Card>
        <CardHeader><CardTitle className="text-sm">Change Plan</CardTitle></CardHeader>
        <CardContent className="flex items-center gap-3">
          <Select value={newPlanId || sub.plan_id} onValueChange={setNewPlanId}>
            <SelectTrigger className="w-48"><SelectValue /></SelectTrigger>
            <SelectContent>
              {plans.map((p) => <SelectItem key={p.plan_id} value={p.plan_id}>{p.name} (${(p.monthly_price_cents / 100).toFixed(2)}/mo)</SelectItem>)}
            </SelectContent>
          </Select>
          <Button
            size="sm"
            onClick={() => planMutation.mutate(newPlanId)}
            disabled={!newPlanId || newPlanId === sub.plan_id || planMutation.isPending}
          >
            {planMutation.isPending ? "Updating..." : "Update Plan"}
          </Button>
        </CardContent>
      </Card>

      {/* Cancel */}
      {sub.status !== "CANCELLED" && (
        <div className="flex justify-end">
          <Button
            variant="destructive"
            onClick={() => cancelMutation.mutate()}
            disabled={cancelMutation.isPending}
          >
            {cancelMutation.isPending ? "Cancelling..." : "Cancel Subscription"}
          </Button>
        </div>
      )}
    </div>
  );
}
```

**Note:** `fetchDevicePlans` should be imported from `device-tiers.ts` (the renamed file). Adjust the import path based on whether you rename the file or keep the same filename with new content.

---

## Part 4: Rewrite DeviceTiersPage.tsx → Device Plans Manager

The page currently manages `device_tiers` (just feature flags). Rewrite it to manage `device_plans` which have:
- `plan_id` (string, e.g. "basic", "standard", "premium")
- `name` (display name)
- `description`
- `limits` (JSONB: sensors, data_retention_days, telemetry_rate_per_minute, health_telemetry_interval_seconds)
- `features` (JSONB: ota_updates, advanced_analytics, streaming_export, x509_auth, message_routing, device_commands, device_twin, carrier_diagnostics)
- `monthly_price_cents`, `annual_price_cents`
- `sort_order`, `is_active`

Update the `KNOWN_FEATURES` constant to match the new feature keys:

```typescript
const KNOWN_FEATURES = [
  "ota_updates",
  "advanced_analytics",
  "streaming_export",
  "x509_auth",
  "message_routing",
  "device_commands",
  "device_twin",
  "carrier_diagnostics",
] as const;
```

Update the `KNOWN_LIMITS` for the limits section:

```typescript
const KNOWN_LIMITS = [
  { key: "sensors", label: "Sensors", type: "number" },
  { key: "data_retention_days", label: "Data Retention (days)", type: "number" },
  { key: "telemetry_rate_per_minute", label: "Telemetry Rate (msg/min)", type: "number" },
  { key: "health_telemetry_interval_seconds", label: "Health Interval (sec)", type: "number" },
] as const;
```

Key changes:
1. Replace all `fetchDeviceTiers` → `fetchDevicePlans`, `createDeviceTier` → `createDevicePlan`, `updateDeviceTier` → `updateDevicePlan`
2. Replace `OperatorDeviceTier` → `OperatorDevicePlan`
3. Replace `tier_id` (number) → `plan_id` (string) — the form needs a text input for plan_id, not auto-generated
4. Add limits editing (numeric inputs for each limit key)
5. Add pricing fields (monthly_price_cents, annual_price_cents)
6. Update table columns to show: Plan ID, Name, Limits summary, Features, Price, Sort, Active
7. Update page title to "Device Plans"
8. Update Zod schema to match new model

### Form Schema

```typescript
const devicePlanSchema = z.object({
  plan_id: z.string().min(2).max(50).regex(/^[a-z0-9_-]+$/, "Lowercase alphanumeric with hyphens/underscores"),
  name: z.string().min(2).max(100),
  description: z.string().max(500).optional().or(z.literal("")),
  limits: z.record(z.string(), z.coerce.number()).optional(),
  features: z.record(z.string(), z.boolean()).optional(),
  monthly_price_cents: z.coerce.number().int().min(0),
  annual_price_cents: z.coerce.number().int().min(0),
  sort_order: z.coerce.number().int().min(0).optional(),
  is_active: z.boolean().optional(),
});
```

---

## Part 5: Update OperatorTenantDetailPage.tsx

### Subscription section

Replace the subscription query (line ~79-83) that calls `/operator/subscriptions?tenant_id=...` with:

```typescript
const { data: subscriptionList, refetch: refetchSubscriptions } = useQuery({
  queryKey: ["tenant-device-subscriptions", tenantId],
  queryFn: () => fetchDeviceSubscriptions({ tenant_id: tenantId! }),
  enabled: !!tenantId,
});
```

Import `fetchDeviceSubscriptions` from `@/services/api/operator`.

Update the `Subscription` interface at the top of the file to match `DeviceSubscriptionRow` shape:

```typescript
interface Subscription {
  subscription_id: string;
  tenant_id: string;
  device_id: string;
  plan_id: string;
  status: string;
  term_start: string;
  term_end: string | null;
}
```

Update the table columns to show: Subscription ID, Device, Plan, Term End, Status. Remove the "Type" column and "Devices X/Y" column.

Remove:
- `typeClasses` map (no more MAIN/ADDON/TRIAL/TEMPORARY types)
- The `TypeBadge` rendering in each row
- The `active_device_count / device_limit` cell

Change the subscription table rows:

```tsx
<TableHead>ID</TableHead>
<TableHead>Device</TableHead>
<TableHead>Plan</TableHead>
<TableHead>Term End</TableHead>
<TableHead>Status</TableHead>
```

```tsx
<TableCell className="font-mono text-sm">{subscription.device_id}</TableCell>
<TableCell><Badge variant="outline">{subscription.plan_id}</Badge></TableCell>
```

### Expiry notifications section

**Remove entirely.** The expiry notifications endpoint is deprecated (410). Remove:
- The `fetchExpiryNotifications` import
- The `expiryNotifications` query (lines ~85-92)
- The entire "Expiry Notifications" Card (lines ~406-462)

### Bulk assign dialog

**Remove** the `BulkAssignDialog` import and button. In the new per-device model, bulk assignment doesn't make sense — you create individual device subscriptions. Remove:
- `import { BulkAssignDialog }`
- The `bulkAssignOpen` state
- The "Bulk Assign Devices" button
- The `<BulkAssignDialog>` component render

### Create subscription dialog update

The "Add Subscription" button and `CreateSubscriptionDialog` should be updated to create device subscriptions. See Part 6 below.

---

## Part 6: Update Dialogs

### CreateSubscriptionDialog.tsx

Rewrite for the new model. Creating a device subscription requires:
- `tenant_id` (pre-selected when opened from tenant detail page)
- `device_id` (select from tenant's devices)
- `plan_id` (select from device plans)
- `status` (default ACTIVE)
- `term_end` (date picker)

Remove:
- `subscription_type` selection (MAIN/ADDON/TRIAL/TEMPORARY)
- `device_limit` input
- `parent_subscription_id` selection
- The parent subscription query

Replace with:
- Device list query: `apiGet<{devices: {device_id: string}[]}>(`/operator/tenants/${tenantId}/devices`)` or `/api/v1/operator/devices?tenant_filter=${tenantId}`
- Device plans query: `fetchDevicePlans()`
- Device selector (select which device gets the subscription)
- Plan selector (select which plan)

```tsx
const mutation = useMutation({
  mutationFn: async () => {
    const payload = {
      tenant_id: tenantId,
      device_id: selectedDeviceId,
      plan_id: selectedPlanId,
      status: "ACTIVE",
      term_end: termEnd ? new Date(termEnd).toISOString() : undefined,
    };
    return apiPost("/api/v1/operator/device-subscriptions", payload);
  },
  ...
});
```

### EditSubscriptionDialog.tsx

Simplify significantly. The new model only allows updating:
- `plan_id` (change plan)
- `status` (change status)
- `term_end` (extend/change term)

Remove:
- `device_limit` input (each subscription = 1 device)
- The complex confirmation dialog for limit reduction (no longer applicable)
- Quick extend buttons can stay (they're useful)
- Quick activate/suspend can stay

Update the mutation to call:
```tsx
apiPatch(`/api/v1/operator/device-subscriptions/${subscriptionId}`, data)
```

Instead of:
```tsx
apiPost(`/operator/tenants/${tenantId}/subscription`, data)
```

### StatusChangeDialog.tsx

Update the API call from:
```tsx
apiPatch(`/operator/subscriptions/${subscription.subscription_id}`, { status, notes })
```
To:
```tsx
apiPatch(`/api/v1/operator/device-subscriptions/${subscription.subscription_id}`, { status: newStatus })
```

Note: The new endpoint doesn't accept `notes`. Remove the notes field from the payload (or keep the UI input for operator reference but don't send to API).

### DeviceSubscriptionDialog.tsx

This dialog assigns a device to a subscription. In the new model, this means creating a new device subscription. Update the query from `/operator/subscriptions?...` to `/api/v1/operator/device-subscriptions?...`. Update the mutation endpoint accordingly.

### BulkAssignDialog.tsx

**Delete this file.** It's not applicable to the per-device subscription model. Each subscription is created individually per device.

### SubscriptionInfoCards.tsx

Update to use `DeviceSubscriptionRow` shape instead of `SubscriptionDetail`. Remove the "Device Usage" card (no device_limit concept). Keep the "Term Period" card. Change the "Tenant" card if needed.

Alternatively, since the detail page is being simplified to handle this inline, this component may become unused. If so, delete it.

### SubscriptionDeviceList.tsx

**Delete this file.** In the new model, each subscription = 1 device. There's no "list of devices in a subscription." The device is shown directly on the detail page.

---

## Part 7: Update Navigation and Routing

### AppSidebar.tsx

Update `operatorTenantNav` (around line 96-101):

```typescript
const operatorTenantNav: NavItem[] = [
  { label: "Tenants", href: "/operator/tenants", icon: Building2 },
  { label: "Health Matrix", href: "/operator/tenant-matrix", icon: LayoutGrid },
  { label: "Subscriptions", href: "/operator/subscriptions", icon: CreditCard },
  { label: "Device Plans", href: "/operator/device-plans", icon: Layers },
  { label: "Account Tiers", href: "/operator/account-tiers", icon: Shield },
];
```

Changes:
- "Device Tiers" → "Device Plans" with href `/operator/device-plans`
- Add "Account Tiers" with href `/operator/account-tiers`

### router.tsx

Update the operator routes (around lines 157-159):

```typescript
{ path: "subscriptions", element: <SubscriptionsPage /> },
{ path: "subscriptions/:subscriptionId", element: <SubscriptionDetailPage /> },
{ path: "device-plans", element: <DeviceTiersPage /> },  // reused component, now manages plans
{ path: "account-tiers", element: <AccountTiersPage /> }, // new page (optional — see below)
```

Remove the `device-tiers` route. Add `device-plans` route pointing to the rewritten `DeviceTiersPage` component.

### Account Tiers Page (Optional)

If you want an operator page for managing account tiers, create `frontend/src/features/operator/AccountTiersPage.tsx`. It would be very similar to the Device Plans page but with:
- `limits`: users, alert_rules, notification_channels, dashboards_per_user, device_groups, api_requests_per_minute
- `features`: sso, custom_branding, audit_log_export, bulk_device_import, carrier_self_service, alert_escalation, oncall_scheduling, maintenance_windows
- `support`: level, sla_uptime_pct, response_time_hours, dedicated_csm
- Pricing: monthly_price_cents, annual_price_cents

**If skipping this page for now:** Just remove the "Account Tiers" sidebar entry and route. The tiers are seeded via migration and can be managed via DB/API directly. The page can be added later.

---

## Part 8: Clean Up Dead Imports

After all changes, search for and fix any remaining references to:

```bash
grep -rn "fetchDeviceTiers\|createDeviceTier\|updateDeviceTier\|OperatorDeviceTier" frontend/src/ --include="*.ts" --include="*.tsx"
grep -rn "fetchSubscriptions\|createSubscription\|updateSubscription\|fetchExpiryNotifications" frontend/src/ --include="*.ts" --include="*.tsx" | grep -v "device-subscriptions\|DeviceSubscription"
grep -rn "SubscriptionDeviceList\|SubscriptionInfoCards\|BulkAssignDialog" frontend/src/ --include="*.ts" --include="*.tsx"
grep -rn "device-tiers" frontend/src/ --include="*.ts" --include="*.tsx" | grep -v "device-plans"
grep -rn "ExpiryNotification\|expiring-notifications" frontend/src/ --include="*.ts" --include="*.tsx"
```

Fix or remove all stale references.

---

## Verification

```bash
# TypeScript
cd frontend && npx tsc --noEmit

# Build
cd frontend && npm run build

# Grep for any remaining old endpoint references
grep -rn "/operator/subscriptions" frontend/src/ --include="*.ts" --include="*.tsx" | grep -v "device-subscriptions"
grep -rn "/operator/device-tiers" frontend/src/ --include="*.ts" --include="*.tsx"
# Both should return empty (or only show comments)
```

Then browser verify:
1. Navigate to operator → Subscriptions → should load device subscriptions list (not 410)
2. Navigate to operator → Device Plans → should load plans (not 410)
3. Navigate to operator → Tenants → tenant detail → should show device subscriptions (not 410)
4. No console 410 errors
