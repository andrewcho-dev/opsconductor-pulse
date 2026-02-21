# 009 -- Frontend: Organization Settings, Billing Page, Device Tier Assignment

## Context

Backend endpoints available:
- `GET/PUT /api/v1/customer/organization` — tenant profile
- `GET /api/v1/customer/billing/config` — Stripe config
- `GET /api/v1/customer/billing/status` — subscriptions + tier allocations
- `GET /api/v1/customer/billing/entitlements` — plan limits + usage
- `GET /api/v1/customer/billing/subscriptions` — full subscription list
- `POST /api/v1/customer/billing/checkout-session` — Stripe checkout
- `POST /api/v1/customer/billing/portal-session` — Stripe portal
- `POST /api/v1/customer/billing/addon-checkout` — co-terminated add-on
- `GET /api/v1/customer/device-tiers` — available tiers
- `PUT/DELETE /api/v1/customer/devices/{device_id}/tier` — tier assignment

## Task

### Step 1: Create Organization API Module

Create `frontend/src/services/api/organization.ts`:

```typescript
import { apiGet, apiPut } from "./client";

export interface OrganizationProfile {
  tenant_id: string;
  name: string;
  legal_name: string | null;
  contact_email: string | null;
  contact_name: string | null;
  phone: string | null;
  industry: string | null;
  company_size: string | null;
  address_line1: string | null;
  address_line2: string | null;
  city: string | null;
  state_province: string | null;
  postal_code: string | null;
  country: string | null;
  data_residency_region: string | null;
  support_tier: string | null;
  sla_level: number | null;
  billing_email: string | null;
  created_at: string;
  updated_at: string;
}

export interface OrganizationUpdate {
  name?: string;
  legal_name?: string;
  phone?: string;
  industry?: string;
  company_size?: string;
  address_line1?: string;
  address_line2?: string;
  city?: string;
  state_province?: string;
  postal_code?: string;
  country?: string;
  billing_email?: string;
}

export async function getOrganization(): Promise<OrganizationProfile> {
  return apiGet("/api/v1/customer/organization");
}

export async function updateOrganization(data: OrganizationUpdate): Promise<OrganizationProfile> {
  return apiPut("/api/v1/customer/organization", data);
}
```

### Step 2: Create Billing API Module

Create `frontend/src/services/api/billing.ts`:

```typescript
import { apiGet, apiPost, apiPut, apiDelete } from "./client";

export interface BillingConfig {
  stripe_configured: boolean;
  publishable_key: string | null;
}

export interface TierAllocation {
  subscription_id: string;
  tier_id: number;
  tier_name: string;
  tier_display_name: string;
  slot_limit: number;
  slots_used: number;
  slots_available: number;
}

export interface SubscriptionInfo {
  subscription_id: string;
  subscription_type: string;
  plan_id: string | null;
  status: string;
  device_limit: number;
  active_device_count: number;
  stripe_subscription_id: string | null;
  parent_subscription_id: string | null;
  description: string | null;
  term_start: string | null;
  term_end: string | null;
  grace_end?: string | null;
  is_stripe_managed?: boolean;
}

export interface BillingStatus {
  has_billing_account: boolean;
  billing_email: string | null;
  support_tier: string | null;
  sla_level: number | null;
  subscriptions: SubscriptionInfo[];
  tier_allocations: TierAllocation[];
}

export interface EntitlementInfo {
  current: number;
  limit: number;
}

export interface PlanUsage {
  plan_id: string | null;
  usage: {
    alert_rules: EntitlementInfo;
    notification_channels: EntitlementInfo;
    users: EntitlementInfo;
    devices: { current: number; limit: number | null };
  };
}

export interface DeviceTier {
  tier_id: number;
  name: string;
  display_name: string;
  description: string;
  features: Record<string, boolean>;
}

export async function getBillingConfig(): Promise<BillingConfig> {
  return apiGet("/api/v1/customer/billing/config");
}

export async function getBillingStatus(): Promise<BillingStatus> {
  return apiGet("/api/v1/customer/billing/status");
}

export async function getEntitlements(): Promise<PlanUsage> {
  return apiGet("/api/v1/customer/billing/entitlements");
}

export async function createCheckoutSession(data: {
  price_id: string;
  success_url: string;
  cancel_url: string;
}): Promise<{ url: string }> {
  return apiPost("/api/v1/customer/billing/checkout-session", data);
}

export async function createPortalSession(data: {
  return_url: string;
}): Promise<{ url: string }> {
  return apiPost("/api/v1/customer/billing/portal-session", data);
}

export async function getDeviceTiers(): Promise<DeviceTier[]> {
  const response = await apiGet<{ tiers: DeviceTier[] }>("/api/v1/customer/device-tiers");
  return response.tiers;
}

export async function assignDeviceTier(deviceId: string, tierId: number): Promise<void> {
  await apiPut(`/api/v1/customer/devices/${deviceId}/tier`, { tier_id: tierId });
}

export async function removeDeviceTier(deviceId: string): Promise<void> {
  await apiDelete(`/api/v1/customer/devices/${deviceId}/tier`);
}
```

### Step 3: Create Organization Settings Page

Create `frontend/src/features/settings/OrganizationPage.tsx`:

**Layout**: Two sections stacked (or two-column on wide screens).

**Section 1 — "Company Profile"** card:
- Form fields: Name, Legal Name, Phone, Billing Email, Industry (dropdown), Company Size (dropdown)
- Industry options: Manufacturing, Agriculture, Healthcare, Energy & Utilities, Logistics, Retail, Smart Buildings, Technology, Other
- Company Size options: 1-10, 11-50, 51-200, 201-500, 501-1000, 1000+
- Pre-populate from `getOrganization()` via `useQuery({ queryKey: ["organization"] })`
- Save button calls `useMutation({ mutationFn: updateOrganization })`
- `toast.success("Organization updated")` on save

**Section 2 — "Address"** card:
- Fields: Address Line 1, Address Line 2, City, State/Province, Postal Code, Country (2-char input)
- Same form, same save mutation — combine all fields into one `updateOrganization()` call

**Section 3 — "Plan & Support"** card (read-only):
- Display: Data Residency Region, Support Tier, SLA Level
- These are operator-set. Show as plain text with muted labels, no edit controls.

**Follow the pattern from** `features/settings/ProfilePage.tsx`: `useQuery` + `useEffect` to sync form state + `useMutation` + `toast`. Use Shadcn components: `Card`, `CardContent`, `CardHeader`, `CardTitle`, `Button`, `Input`, `Label`, `Select`.

### Step 4: Create Billing Page

Create `frontend/src/features/settings/BillingPage.tsx`:

**Card 1 — "Subscriptions"**:
- Table listing all subscriptions: Type (badge), Plan, Status (StatusBadge), Devices Used/Limit, Term dates
- Show parent relationship for ADDON types
- If `has_billing_account`: "Manage Billing" button → `createPortalSession({ return_url: window.location.href })` → redirect
- If not `has_billing_account` and `stripe_configured`: "Subscribe" button → `createCheckoutSession(...)` → redirect
- "Add Capacity" button for active MAIN subscriptions → opens add-on dialog (or links to addon checkout)
- Use `getBillingStatus()` query

**Card 2 — "Device Tier Allocations"**:
- Table: Tier Name, Slots Used / Slot Limit, progress bar
- Aggregate across all active subscriptions
- Color: green < 75%, yellow 75-90%, red > 90%
- Only show if `tier_allocations` is non-empty

**Card 3 — "Usage & Limits"**:
- Table: Resource (Alert Rules, Channels, Users), Current, Limit, % Used
- Use `getEntitlements()` query
- Same color coding

### Step 5: Add Device Tier Assignment to Device Detail

In `frontend/src/features/devices/DeviceDetailPage.tsx`:

Add a "Device Tier" card/section. Show current tier (if assigned) and allow changing it.

1. Import:
```tsx
import { getDeviceTiers, assignDeviceTier, removeDeviceTier } from "@/services/api/billing";
```

2. Add query:
```tsx
const { data: tiers } = useQuery({
  queryKey: ["device-tiers"],
  queryFn: getDeviceTiers,
});
```

3. Add a tier selector (after existing device info cards):
```tsx
<Card>
  <CardHeader>
    <CardTitle className="text-sm font-medium">Device Tier</CardTitle>
  </CardHeader>
  <CardContent>
    <Select
      value={device?.tier_id?.toString() || "none"}
      onValueChange={async (val) => {
        try {
          if (val === "none") {
            await removeDeviceTier(deviceId!);
          } else {
            await assignDeviceTier(deviceId!, parseInt(val));
          }
          queryClient.invalidateQueries({ queryKey: ["device", deviceId] });
          toast.success("Device tier updated");
        } catch (err: any) {
          toast.error(err?.message || "Failed to update tier");
        }
      }}
    >
      <SelectTrigger>
        <SelectValue placeholder="Select tier..." />
      </SelectTrigger>
      <SelectContent>
        <SelectItem value="none">No tier assigned</SelectItem>
        {tiers?.map((tier) => (
          <SelectItem key={tier.tier_id} value={tier.tier_id.toString()}>
            {tier.display_name}
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  </CardContent>
</Card>
```

**Important**: Verify the device detail GET response includes `tier_id`. If the backend device detail query was updated in task 007, `device.tier_id` should be available. If not, the tier selector will default to "No tier assigned".

### Step 6: Register Routes

In `frontend/src/app/router.tsx`:

```tsx
import OrganizationPage from "@/features/settings/OrganizationPage";
import BillingPage from "@/features/settings/BillingPage";

// Inside RequireCustomer children:
{ path: "settings/organization", element: <OrganizationPage /> },
{ path: "billing", element: <BillingPage /> },
```

### Step 7: Update Sidebar Navigation

In `frontend/src/components/layout/AppSidebar.tsx`:

Add to the `settingsNav` array (around line 160). Add `Building2` to the lucide-react import if not already imported. Use `Receipt` or `CreditCard` for billing (CreditCard is already imported).

```tsx
{ label: "Organization", href: "/settings/organization", icon: Building2 },
{ label: "Billing", href: "/billing", icon: CreditCard },
```

Place Organization after Profile and Billing after Subscription in the nav order.

## Verify

```bash
# 1. Build frontend
cd frontend && npm run build

# 2. Type check
npx tsc --noEmit

# 3. Navigate to /settings/organization → see company profile form
# 4. Navigate to /billing → see subscriptions, tier allocations, usage
# 5. Navigate to device detail → see tier selector dropdown
# 6. Edit org fields, save → toast success
```

## Commit

```
feat(phase134): add customer organization settings, billing page, and tier assignment UI

Create OrganizationPage with company profile and address editing.
Create BillingPage showing subscriptions table, device tier slot
allocations with progress bars, and plan usage/limits summary.
Add Manage Billing and Subscribe action buttons for Stripe integration.
Add device tier selector to DeviceDetailPage with assign/remove.
Register routes and sidebar navigation items.
```
