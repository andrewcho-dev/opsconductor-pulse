# Task 005 — Frontend: Types, API Functions, Billing Pages

## Files

1. Update `frontend/src/services/api/types.ts` — new types
2. Update `frontend/src/services/api/billing.ts` — new API functions, updated response types
3. Rewrite `frontend/src/features/subscription/SubscriptionPage.tsx` — account tier + device subscriptions view
4. Rewrite `frontend/src/features/subscription/RenewalPage.tsx` — tier/plan upgrade flows
5. Update `frontend/src/features/settings/BillingPage.tsx` — entitlements display for new model

## Part 1: Types (`types.ts`)

Add these types (remove old `SubscriptionInfo`, `PlanUsage` etc.):

```typescript
// ─── Account Tiers ──────────────────────────────────────

export interface AccountTier {
  tier_id: string;
  name: string;
  description: string;
  limits: {
    users?: number;
    alert_rules?: number;
    notification_channels?: number;
    dashboards_per_user?: number;
    device_groups?: number;
    api_requests_per_minute?: number;
  };
  features: {
    sso?: boolean;
    custom_branding?: boolean;
    audit_log_export?: boolean;
    bulk_device_import?: boolean;
    carrier_self_service?: boolean;
    alert_escalation?: boolean;
    oncall_scheduling?: boolean;
    maintenance_windows?: boolean;
  };
  support: {
    level?: string;
    sla_uptime_pct?: number | null;
    response_time_hours?: number | null;
    dedicated_csm?: boolean;
  };
  monthly_price_cents: number;
  annual_price_cents: number;
  is_active: boolean;
  sort_order: number;
}

// ─── Device Plans ───────────────────────────────────────

export interface DevicePlan {
  plan_id: string;
  name: string;
  description: string;
  limits: {
    sensors?: number;
    data_retention_days?: number;
    telemetry_rate_per_minute?: number;
    health_telemetry_interval_seconds?: number;
  };
  features: {
    ota_updates?: boolean;
    advanced_analytics?: boolean;
    streaming_export?: boolean;
    x509_auth?: boolean;
    message_routing?: boolean;
    device_commands?: boolean;
    device_twin?: boolean;
    carrier_diagnostics?: boolean;
  };
  monthly_price_cents: number;
  annual_price_cents: number;
  is_active: boolean;
  sort_order: number;
}

// ─── Device Subscriptions ───────────────────────────────

export interface DeviceSubscription {
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
}

// ─── Account Entitlements (response from /billing/entitlements) ──

export interface AccountEntitlements {
  tier_id: string | null;
  tier_name: string | null;
  limits: Record<string, number>;
  features: Record<string, boolean>;
  support: {
    level?: string;
    sla_uptime_pct?: number | null;
    response_time_hours?: number | null;
    dedicated_csm?: boolean;
  };
  usage: Record<string, { current: number; limit: number | null }>;
}
```

## Part 2: API Functions (`billing.ts`)

Update the billing API module. Keep existing functions that still work, update signatures:

```typescript
// ─── Account Tiers ──────────────────────────────────────

export async function listAccountTiers(): Promise<{ tiers: AccountTier[] }> {
  return apiGet("/api/v1/customer/billing/account-tiers");
}

// ─── Device Plans ───────────────────────────────────────

export async function listDevicePlans(): Promise<{ plans: DevicePlan[] }> {
  return apiGet("/api/v1/customer/billing/device-plans");
}

// ─── Entitlements (updated response type) ───────────────

export async function getEntitlements(): Promise<AccountEntitlements> {
  return apiGet("/api/v1/customer/billing/entitlements");
}

// ─── Keep existing Stripe functions ─────────────────────
// getBillingStatus, createCheckoutSession, createPortalSession — keep but update types as needed
```

## Part 3: Subscription Page Rewrite (`SubscriptionPage.tsx`)

Replace the current page (which shows one MAIN subscription) with a two-section layout:

### Layout

```
┌────────────────────────────────────────────────────────────────┐
│  Account Tier                                                  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ Growth                                        $49/month  │  │
│  │ 10 users · 100 alert rules · 10 channels                │  │
│  │ Standard support · 99.5% SLA · 8hr response              │  │
│  │                                          [Change Tier ↗] │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                │
│  Device Subscriptions                           4 active       │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │ Device      │ Plan      │ Status │ Term        │ Monthly │ │
│  │ GW-001      │ Standard  │ Active │ Jan–Dec '26 │ $9.99   │ │
│  │ GW-002      │ Standard  │ Active │ Jan–Dec '26 │ $9.99   │ │
│  │ GW-003      │ Basic     │ Active │ Jan–Dec '26 │ $2.99   │ │
│  │ GW-004      │ Premium   │ Active │ Feb–Jan '27 │ $24.99  │ │
│  └───────────────────────────────────────────────────────────┘ │
│                                                                │
│  Monthly Total: $49.00 + $47.96 = $96.96                      │
└────────────────────────────────────────────────────────────────┘
```

### Data Fetching

```tsx
const entitlements = useQuery({ queryKey: ["entitlements"], queryFn: getEntitlements });
const tiers = useQuery({ queryKey: ["account-tiers"], queryFn: listAccountTiers });
const plans = useQuery({ queryKey: ["device-plans"], queryFn: listDevicePlans });
// Device subscriptions: need a new API endpoint or derive from device list
```

### Device Subscription Table

Use `DataTable` component. Columns: Device ID, Plan (badge), Status (badge), Term Period, Monthly Price.

### "Change Tier" Button

Links to the renewal/upgrade page or triggers a Stripe checkout session for the new tier.

## Part 4: Renewal Page Rewrite (`RenewalPage.tsx`)

Replace the hardcoded `RENEWAL_OPTIONS` with data from `listAccountTiers()` and `listDevicePlans()`.

Two sections:
1. **Account Tier Selection** — card for each tier with features comparison
2. **Device Plan Selection** — card for each plan with capabilities comparison

Each card shows:
- Name, price, description
- Key limits and features (checkmarks for included features)
- "Current" badge on the active tier/plan
- "Select" button for upgrades (triggers Stripe checkout)

## Part 5: Billing Page Update (`BillingPage.tsx`)

Update the entitlements display to use the new `AccountEntitlements` response:

```tsx
// Show account tier info at top
<div>
  <h3>Account Tier: {entitlements.tier_name}</h3>
  <p>Support: {entitlements.support.level} · SLA: {entitlements.support.sla_uptime_pct}%</p>
</div>

// Usage progress bars (existing pattern)
{Object.entries(entitlements.usage).map(([key, { current, limit }]) => (
  <UsageBar key={key} label={key} current={current} limit={limit} />
))}

// Features list (checkmarks)
{Object.entries(entitlements.features).map(([key, enabled]) => (
  <FeatureRow key={key} label={key} enabled={enabled} />
))}
```

## Part 6: Remove Old Types

Remove from `types.ts`:
- `SubscriptionInfo` (if it referenced old subscription_plans model)
- `PlanUsage` (replaced by `AccountEntitlements`)
- `TierAllocation` (no longer exists)
- Any type referencing `device_tiers` or `plan_tier_defaults`

## Verification

```bash
cd frontend && npx tsc --noEmit && npm run build
```
