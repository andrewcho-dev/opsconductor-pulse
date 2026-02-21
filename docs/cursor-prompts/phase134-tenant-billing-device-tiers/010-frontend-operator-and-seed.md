# 010 -- Frontend: Operator Enhancements + Seed Data

## Context

Backend enriched tenant CRUD and device tier management endpoints are ready. This task updates the operator frontend and seed data to exercise all new features.

## Task

### Step 1: Update Tenant TypeScript Interfaces

In `frontend/src/services/api/tenants.ts`:

**Extend `Tenant` interface** with all enriched fields:
```typescript
export interface Tenant {
  tenant_id: string;
  name: string;
  status: string;
  contact_email?: string;
  contact_name?: string;
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
  data_residency_region?: string;
  support_tier?: string;
  sla_level?: number;
  stripe_customer_id?: string;
  billing_email?: string;
  metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}
```

**Extend `TenantCreate`** and **`TenantUpdate`** similarly — add all new optional fields. `TenantUpdate` also gets `stripe_customer_id`.

### Step 2: Extend Edit Tenant Dialog

In `frontend/src/features/operator/EditTenantDialog.tsx`:

**Expand the dialog** from `max-w-md` to `max-w-2xl max-h-[80vh] overflow-y-auto`.

**Organize into sections** using headings or `<fieldset>` groups:

**Section 1: Basic Info**
- Display Name (existing)
- Legal Name (new)
- Contact Name (existing), Contact Email (existing) — 2-col grid
- Phone (new), Billing Email (new) — 2-col grid

**Section 2: Company Details**
- Industry — dropdown: Manufacturing, Agriculture, Healthcare, Energy & Utilities, Logistics, Retail, Smart Buildings, Technology, Other
- Company Size — dropdown: 1-10, 11-50, 51-200, 201-500, 501-1000, 1000+

**Section 3: Address**
- Address Line 1, Address Line 2
- City, State/Province — 2-col grid
- Postal Code, Country (2-char) — 2-col grid

**Section 4: Operations** (operator-only fields)
- Data Residency Region — dropdown: us-east, us-west, eu-west, eu-central, ap-southeast, ap-northeast
- Support Tier — dropdown: developer, standard, business, enterprise
- SLA Level — number input (e.g., 99.90)
- Stripe Customer ID — text input (manual link)
- Status (existing)

Add state variables for all new fields. Sync from `tenant` prop in `useEffect`. Include all fields in the `mutation.mutate()` call.

### Step 3: Add Company Profile Card to Tenant Detail

In `frontend/src/features/operator/OperatorTenantDetailPage.tsx`:

**Fetch full tenant data** including enriched fields. The existing `fetchTenantStats` may not return all profile fields. Add a query for the full tenant record:

```tsx
const { data: fullTenant } = useQuery({
  queryKey: ["tenant-detail", tenantId],
  queryFn: () => fetchTenant(tenantId!),
  enabled: !!tenantId,
});
```

**Add a "Company Profile" card** between the stats cards and the subscriptions table:

```
┌─────────────────────────────────────────────────────┐
│ Company Profile                              [Edit] │
├─────────────────────────────────────────────────────┤
│ Legal Name   Acme IoT Corporation                   │
│ Industry     Manufacturing    │ Size    51-200       │
│ Phone        +1-555-0100      │ Billing billing@... │
│                                                     │
│ Address                                             │
│ 123 Industrial Blvd, Suite 400                      │
│ Austin, TX 78701 US                                 │
│                                                     │
│ Operations                                          │
│ Region  us-east    │ Support  business              │
│ SLA     99.95%     │ Stripe   cus_abc123            │
└─────────────────────────────────────────────────────┘
```

Use a grid layout with `Label` + text pairs. Show "—" for empty fields. The Edit button opens the `EditTenantDialog`.

Pass `fullTenant` to the `EditTenantDialog` instead of the limited stats data:
```tsx
<EditTenantDialog
  tenant={fullTenant || null}
  open={showEdit}
  onOpenChange={setShowEdit}
/>
```

### Step 4: Create Operator Device Tier Management Page

Create `frontend/src/features/operator/DeviceTiersPage.tsx`:

**Add API functions** — either to `frontend/src/services/api/operator.ts` or a new `frontend/src/services/api/device-tiers.ts`:

```typescript
export interface OperatorDeviceTier {
  tier_id: number;
  name: string;
  display_name: string;
  description: string;
  features: Record<string, boolean>;
  sort_order: number;
  is_active: boolean;
  created_at: string;
}

export async function fetchDeviceTiers(): Promise<{ tiers: OperatorDeviceTier[] }> {
  return apiGet("/api/v1/operator/device-tiers");
}

export async function createDeviceTier(data: {
  name: string;
  display_name: string;
  description?: string;
  features: Record<string, boolean>;
  sort_order: number;
}): Promise<OperatorDeviceTier> {
  return apiPost("/api/v1/operator/device-tiers", data);
}

export async function updateDeviceTier(
  tierId: number,
  data: { display_name?: string; description?: string; features?: Record<string, boolean>; sort_order?: number; is_active?: boolean }
): Promise<OperatorDeviceTier> {
  return apiPut(`/api/v1/operator/device-tiers/${tierId}`, data);
}
```

**Page layout**:
- Table with columns: Name, Display Name, Description, Features (colored badges), Sort Order, Active (toggle), Actions (Edit)
- "Create Tier" button opens a create dialog
- Feature badges: green for enabled features, gray/muted for disabled
- Known features: telemetry, alerts, dashboards, ota, analytics, x509_auth, streaming_export, message_routing

**Create/Edit dialog**:
- Name (text input, lowercase, only on create)
- Display Name (text input)
- Description (textarea)
- Features: toggle switches for each known feature
- Sort Order (number input)
- Is Active (checkbox, only on edit)

### Step 5: Register Routes and Navigation

In `frontend/src/app/router.tsx`:
```tsx
import DeviceTiersPage from "@/features/operator/DeviceTiersPage";

// Inside RequireOperator children:
{ path: "operator/device-tiers", element: <DeviceTiersPage /> },
```

In `frontend/src/components/layout/AppSidebar.tsx`, add to operator navigation:
```tsx
{ label: "Device Tiers", href: "/operator/device-tiers", icon: Layers },
```
Import `Layers` from lucide-react. Place it after "Subscriptions" in the nav array.

### Step 6: Update Seed Data

In `scripts/seed_demo_data.py`:

**Update `seed_tenants()`** with enriched profiles:

```python
tenant_profiles = {
    "tenant-a": {
        "name": "Acme IoT Corp",
        "legal_name": "Acme IoT Corporation",
        "contact_email": "admin@acme-iot.example.com",
        "contact_name": "Jane Doe",
        "phone": "+1-555-0100",
        "industry": "Manufacturing",
        "company_size": "51-200",
        "address_line1": "123 Industrial Blvd",
        "address_line2": "Suite 400",
        "city": "Austin",
        "state_province": "TX",
        "postal_code": "78701",
        "country": "US",
        "data_residency_region": "us-east",
        "support_tier": "business",
        "sla_level": 99.95,
        "billing_email": "billing@acme-iot.example.com",
    },
    "tenant-b": {
        "name": "Nordic Sensors AB",
        "legal_name": "Nordic Sensors Aktiebolag",
        "contact_email": "ops@nordicsensors.example.com",
        "contact_name": "Erik Lindqvist",
        "phone": "+46-8-555-1234",
        "industry": "Agriculture",
        "company_size": "11-50",
        "address_line1": "Storgatan 12",
        "address_line2": None,
        "city": "Stockholm",
        "state_province": "Stockholm",
        "postal_code": "111 23",
        "country": "SE",
        "data_residency_region": "eu-west",
        "support_tier": "standard",
        "sla_level": 99.90,
        "billing_email": "finance@nordicsensors.example.com",
    },
}
```

Use `ON CONFLICT (tenant_id) DO UPDATE SET ...` to update existing rows.

**Add `seed_tier_allocations()`** — copy from `plan_tier_defaults` for existing subscriptions:
```python
async def seed_tier_allocations(pool):
    async with pool.acquire() as conn:
        subs = await conn.fetch(
            "SELECT subscription_id, plan_id FROM subscriptions WHERE status IN ('ACTIVE', 'TRIAL') AND plan_id IS NOT NULL"
        )
        for sub in subs:
            defaults = await conn.fetch(
                "SELECT tier_id, slot_limit FROM plan_tier_defaults WHERE plan_id = $1", sub["plan_id"]
            )
            for d in defaults:
                await conn.execute(
                    """
                    INSERT INTO subscription_tier_allocations (subscription_id, tier_id, slot_limit)
                    VALUES ($1, $2, $3) ON CONFLICT (subscription_id, tier_id) DO NOTHING
                    """,
                    sub["subscription_id"], d["tier_id"], d["slot_limit"],
                )
```

**Add `seed_device_tiers()`** — assign random tiers to demo devices:
```python
async def seed_device_tiers(pool):
    async with pool.acquire() as conn:
        devices = await conn.fetch(
            "SELECT device_id, tenant_id FROM device_registry WHERE tier_id IS NULL LIMIT 20"
        )
        tiers = await conn.fetch("SELECT tier_id FROM device_tiers WHERE is_active = true ORDER BY sort_order")
        tier_ids = [t["tier_id"] for t in tiers]
        for i, dev in enumerate(devices):
            if tier_ids:
                await conn.execute(
                    "UPDATE device_registry SET tier_id = $1 WHERE device_id = $2 AND tenant_id = $3",
                    tier_ids[i % len(tier_ids)], dev["device_id"], dev["tenant_id"],
                )
```

**Ensure existing subscription seed sets `plan_id`**. If `seed_subscriptions()` doesn't set `plan_id`, add it:
```python
plan_id = "pro"  # or "starter" for tenant-b
```

**Call new functions** in `main()`:
```python
await seed_tier_allocations(pool)
await seed_device_tiers(pool)
```

## Verify

```bash
# 1. Build frontend
cd frontend && npm run build && npx tsc --noEmit

# 2. Seed data
docker compose -f compose/docker-compose.yml exec ui python -m scripts.seed_demo_data

# 3. Verify seed
docker compose -f compose/docker-compose.yml exec db psql -U iot -d pulse \
  -c "SELECT tenant_id, name, industry, country, support_tier FROM tenants"

docker compose -f compose/docker-compose.yml exec db psql -U iot -d pulse \
  -c "SELECT sta.subscription_id, dt.name, sta.slot_limit FROM subscription_tier_allocations sta JOIN device_tiers dt ON dt.tier_id = sta.tier_id"

docker compose -f compose/docker-compose.yml exec db psql -U iot -d pulse \
  -c "SELECT device_id, tier_id FROM device_registry WHERE tier_id IS NOT NULL LIMIT 10"

# 4. Browser verification:
# - Operator tenant detail → company profile card with all fields
# - Operator edit tenant → expanded form with 4 sections
# - Operator device tiers page → Basic/Standard/Premium with feature badges
# - Customer org settings → pre-populated form
# - Customer billing → tier allocations + usage
# - Customer device detail → tier dropdown
```

## Commit

```
feat(phase134): add operator tenant enrichment, device tier UI, and seed data

Extend EditTenantDialog with company profile, address, and operations
sections. Add company profile card to OperatorTenantDetailPage.
Create DeviceTiersPage with feature toggle badges and create/edit
dialogs. Update Tenant interfaces with all enriched fields.
Update seed data with realistic company profiles, tier allocations
from plan_tier_defaults, and random device tier assignments.
```
