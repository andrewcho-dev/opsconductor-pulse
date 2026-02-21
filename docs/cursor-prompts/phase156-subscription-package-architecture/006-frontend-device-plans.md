# Task 006 — Frontend: Device Plan Assignment + Account Tier Display

## Files

1. Update `frontend/src/features/devices/DeviceDetailPage.tsx` — show current device plan
2. Create `frontend/src/features/devices/DevicePlanPanel.tsx` — plan info + upgrade panel on device detail
3. Update `frontend/src/features/settings/CarrierIntegrationsPage.tsx` — use account feature check
4. Update `frontend/src/components/layout/AppSidebar.tsx` — update subscription nav if needed
5. Update `frontend/src/app/router.tsx` — update routes if needed

## Part 1: DevicePlanPanel (`DevicePlanPanel.tsx`)

A panel on the device detail page showing the device's current plan, usage vs limits, and plan upgrade option.

### Layout

```
┌──────────────────────────────────────────────────────────────┐
│  Device Plan                                                  │
│  Standard · $9.99/month                     [Change Plan ↗]  │
│                                                               │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐            │
│  │ Sensors      │ │ Retention   │ │ Telemetry    │            │
│  │ 12 / 15      │ │ 90 days     │ │ 60 msg/min   │            │
│  └─────────────┘ └─────────────┘ └─────────────┘            │
│                                                               │
│  Features                                                     │
│  ✓ OTA Updates    ✓ Analytics    ✓ Streaming Export           │
│  ✗ x509 Auth      ✗ Msg Routing  ✓ Device Commands           │
│  ✓ Device Twin    ✓ Carrier Diag                              │
│                                                               │
│  Subscription: ACTIVE · Jan 1 – Dec 31, 2026                │
└──────────────────────────────────────────────────────────────┘
```

### Implementation

```tsx
interface DevicePlanPanelProps {
  deviceId: string;
}

export function DevicePlanPanel({ deviceId }: DevicePlanPanelProps) {
  // Fetch device plan usage from new entitlements endpoint
  // OR read plan_id from device detail and look up from device_plans list

  const deviceQuery = useQuery({
    queryKey: ["device", deviceId],
    queryFn: () => fetchDevice(deviceId),
  });

  const plansQuery = useQuery({
    queryKey: ["device-plans"],
    queryFn: listDevicePlans,
  });

  const plan = plansQuery.data?.plans.find(p => p.plan_id === deviceQuery.data?.plan_id);

  // Sensor count for usage bar
  const sensorsQuery = useQuery({
    queryKey: ["sensors", deviceId],
    queryFn: () => listDeviceSensors(deviceId),
  });

  const sensorCount = sensorsQuery.data?.sensors?.length ?? 0;
  const sensorLimit = plan?.limits.sensors ?? 0;

  // ... render panel
}
```

### Stat Cards Row

3 stat cards showing plan limits:

```tsx
<div className="grid grid-cols-3 gap-2">
  <StatCard label="Sensors" value={`${sensorCount} / ${sensorLimit}`} />
  <StatCard label="Retention" value={`${plan.limits.data_retention_days} days`} />
  <StatCard label="Telemetry" value={`${plan.limits.telemetry_rate_per_minute} msg/min`} />
</div>
```

### Features Grid

Render each feature as a row with checkmark or X:

```tsx
const FEATURE_LABELS: Record<string, string> = {
  ota_updates: "OTA Updates",
  advanced_analytics: "Analytics",
  streaming_export: "Streaming Export",
  x509_auth: "x509 Auth",
  message_routing: "Message Routing",
  device_commands: "Device Commands",
  device_twin: "Device Twin",
  carrier_diagnostics: "Carrier Diagnostics",
};

<div className="grid grid-cols-3 gap-1 text-xs">
  {Object.entries(FEATURE_LABELS).map(([key, label]) => (
    <div key={key} className="flex items-center gap-1">
      {plan.features[key] ? (
        <Check className="h-3 w-3 text-green-500" />
      ) : (
        <X className="h-3 w-3 text-muted-foreground" />
      )}
      <span className={plan.features[key] ? "" : "text-muted-foreground"}>{label}</span>
    </div>
  ))}
</div>
```

### Change Plan Dialog

A `Dialog` with a grid of plan cards (from `listDevicePlans`). Each card shows name, price, key limits. Click selects, confirm triggers plan change API call:

```tsx
// PUT /api/v1/customer/devices/{deviceId}/plan
// Body: { plan_id: "premium" }
```

Use `useMutation` with toast notification on success, invalidate device + entitlements queries.

### Subscription Status

Show subscription status, term dates at bottom of panel:

```tsx
<div className="text-xs text-muted-foreground flex gap-2">
  <Badge variant={statusVariant}>{subscription.status}</Badge>
  <span>
    {format(new Date(subscription.term_start), "MMM d, yyyy")} –
    {subscription.term_end ? format(new Date(subscription.term_end), "MMM d, yyyy") : "Open-ended"}
  </span>
</div>
```

## Part 2: Add to DeviceDetailPage

In `DeviceDetailPage.tsx`:

```tsx
import { DevicePlanPanel } from "./DevicePlanPanel";

// Add as the FIRST panel in the stack (most important context):
{deviceId && <DevicePlanPanel deviceId={deviceId} />}
```

## Part 3: Update CarrierIntegrationsPage

In `CarrierIntegrationsPage.tsx`, use the entitlements to check `carrier_self_service`:

```tsx
const entitlements = useQuery({
  queryKey: ["entitlements"],
  queryFn: getEntitlements,
});

const isSelfService = entitlements.data?.features?.carrier_self_service ?? false;
```

If `isSelfService` is false:
- Hide "Add Carrier" button
- Hide Edit/Delete buttons on integration cards
- Show info banner: "Carrier integrations are managed by your service provider. Contact support to make changes."

## Part 4: Update Device Type

In `types.ts`, update the `Device` interface to include `plan_id`:

```typescript
export interface Device {
  // ... existing fields ...
  plan_id: string | null;
  // Remove tier_id if present
}
```

## Part 5: Device List — Plan Column

In the device list page/table, add a "Plan" column showing a badge with the device's plan name:

```tsx
{
  accessorKey: "plan_id",
  header: "Plan",
  cell: ({ row }) => {
    const planId = row.getValue("plan_id") as string | null;
    return planId ? <Badge variant="outline">{planId}</Badge> : <span className="text-muted-foreground">—</span>;
  },
}
```

## Verification

```bash
cd frontend && npx tsc --noEmit && npm run build
```

Then browser check:
1. Device detail page → DevicePlanPanel shows plan info, sensor usage, features grid
2. Device list → "Plan" column shows plan badges
3. Carrier settings page → respects carrier_self_service feature flag
4. Subscription page → shows account tier + device subscription table
