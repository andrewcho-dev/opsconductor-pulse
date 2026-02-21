# Task 003 — Carrier Diagnostics Panel (Device Detail)

## File

Create `frontend/src/features/devices/DeviceCarrierPanel.tsx`

Add to `DeviceDetailPage.tsx` as a new panel in the vertical stack.

## Purpose

A panel on the device detail page showing live carrier status, data usage, and network diagnostics for devices linked to a carrier integration. If the device has no carrier link, show an empty state with a "Link to Carrier" prompt.

## Layout

```
┌──────────────────────────────────────────────────────────────────┐
│  Carrier Integration                                [Refresh ↻] │
│  Hologram · HOL-ACME-2024-001                                    │
│                                                                  │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌────────────┐│
│  │ SIM Status   │ │ Network      │ │ IP Address   │ │ Signal     ││
│  │ 🟢 Active    │ │ LTE-M        │ │ 10.176.42.101│ │ 78%        ││
│  └─────────────┘ └─────────────┘ └─────────────┘ └────────────┘│
│                                                                  │
│  Data Usage                                                      │
│  ┌──────────────────────────────────────────────────────────────┐│
│  │ ████████████░░░░░░░░░░░░░░░░░░░░░░░░░░  127.5 / 500 MB     ││
│  │ 25.5% used · Billing: Feb 1 – Feb 28                        ││
│  │ SMS: 3                                                       ││
│  └──────────────────────────────────────────────────────────────┘│
│                                                                  │
│  Network Diagnostics                                             │
│  ┌──────────────────────────────────────────────────────────────┐│
│  │ ICCID: 8901260012345678901                                   ││
│  │ Carrier Device ID: 123456                                    ││
│  │ Last Connection: Feb 18, 10:30 AM                            ││
│  │ Network Type: LTE-M                                          ││
│  └──────────────────────────────────────────────────────────────┘│
│                                                                  │
│  [Activate] [Suspend] [Deactivate] [Reboot]  ← action buttons   │
└──────────────────────────────────────────────────────────────────┘
```

## Implementation

### Props

```tsx
interface DeviceCarrierPanelProps {
  deviceId: string;
}
```

### Data Fetching

Three parallel queries using `useQuery`:

```tsx
const statusQuery = useQuery({
  queryKey: ["carrier-status", deviceId],
  queryFn: () => getCarrierStatus(deviceId),
  refetchInterval: 60_000,  // Refresh every 60s
});

const usageQuery = useQuery({
  queryKey: ["carrier-usage", deviceId],
  queryFn: () => getCarrierUsage(deviceId),
  refetchInterval: 300_000,  // Refresh every 5 min
});

const diagnosticsQuery = useQuery({
  queryKey: ["carrier-diagnostics", deviceId],
  queryFn: () => getCarrierDiagnostics(deviceId),
  refetchInterval: 300_000,
});
```

Import from `@/services/api/carrier`:
```tsx
import { getCarrierStatus, getCarrierUsage, getCarrierDiagnostics } from "@/services/api/carrier";
```

### Unlinked State

If `statusQuery.data?.linked === false`, render an empty state:

```tsx
<div className="rounded-md border border-border p-3 space-y-3">
  <h3 className="text-sm font-medium">Carrier Integration</h3>
  <div className="text-center py-6 text-muted-foreground text-sm">
    <Radio className="h-8 w-8 mx-auto mb-2 opacity-40" />
    <p>No carrier integration linked to this device.</p>
    <p className="text-xs mt-1">Link a carrier in device settings to enable diagnostics.</p>
  </div>
</div>
```

Use `Radio` from `lucide-react`.

### Linked State — Status Section

4 stat cards in a grid:

```tsx
<div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
  <StatCard label="SIM Status" value={info.sim_status} variant={simStatusVariant} />
  <StatCard label="Network" value={info.network_type || "—"} />
  <StatCard label="IP Address" value={info.ip_address || "—"} />
  <StatCard label="Signal" value={info.signal_strength != null ? `${info.signal_strength}%` : "—"} />
</div>
```

`StatCard` is a small inline component (same pattern as `DeviceHealthPanel` from Phase 151):
```tsx
function StatCard({ label, value, variant }: { label: string; value: string; variant?: string }) {
  return (
    <div className="rounded border p-2 text-center">
      <div className="text-xs text-muted-foreground">{label}</div>
      <div className="text-sm font-medium mt-0.5">
        {variant && <Badge variant={variant === "active" ? "default" : "secondary"} className="mr-1">{value}</Badge>}
        {!variant && value}
      </div>
    </div>
  );
}
```

SIM status badge variants:
- `"active"` → `default` (green-ish) badge
- `"suspended"` → `destructive` badge
- `"inactive"` / `"deactivated"` → `secondary` badge
- Others → `outline` badge

### Linked State — Usage Section

Data usage progress bar + details:

```tsx
<div className="space-y-1.5">
  <h4 className="text-xs font-medium text-muted-foreground">Data Usage</h4>
  <div className="space-y-1">
    <div className="flex justify-between text-xs">
      <span>{usage.data_used_mb.toFixed(1)} MB used</span>
      {usage.data_limit_mb && <span>{usage.data_limit_mb} MB limit</span>}
    </div>
    <Progress value={usage.usage_pct} className="h-2" />
    <div className="flex justify-between text-xs text-muted-foreground">
      <span>{usage.usage_pct.toFixed(1)}% used</span>
      {usage.billing_cycle_start && usage.billing_cycle_end && (
        <span>
          {format(new Date(usage.billing_cycle_start), "MMM d")} – {format(new Date(usage.billing_cycle_end), "MMM d")}
        </span>
      )}
    </div>
    {usage.sms_count > 0 && (
      <div className="text-xs text-muted-foreground">SMS: {usage.sms_count}</div>
    )}
  </div>
</div>
```

Import `Progress` from `@/components/ui/progress`.
Import `format` from `date-fns`.

Color the progress bar:
- `< 50%` → default (blue/primary)
- `50-80%` → yellow/warning (add className override)
- `> 80%` → red/destructive (add className override)

### Linked State — Diagnostics Section

Key-value list of network diagnostics:

```tsx
<div className="space-y-1.5">
  <h4 className="text-xs font-medium text-muted-foreground">Network Details</h4>
  <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-xs">
    <DetailRow label="ICCID" value={info.iccid} />
    <DetailRow label="Carrier Device ID" value={info.carrier_device_id} />
    <DetailRow label="Network Status" value={info.network_status} />
    <DetailRow label="Last Connection" value={info.last_connection ? format(new Date(info.last_connection), "MMM d, h:mm a") : "—"} />
  </div>
</div>
```

`DetailRow` is a simple inline component:
```tsx
function DetailRow({ label, value }: { label: string; value: string | null | undefined }) {
  return (
    <>
      <span className="text-muted-foreground">{label}</span>
      <span className="font-mono">{value || "—"}</span>
    </>
  );
}
```

### Refresh Button

In the panel header, add a refresh button that invalidates all three queries:

```tsx
<Button
  variant="ghost"
  size="sm"
  onClick={() => {
    queryClient.invalidateQueries({ queryKey: ["carrier-status", deviceId] });
    queryClient.invalidateQueries({ queryKey: ["carrier-usage", deviceId] });
    queryClient.invalidateQueries({ queryKey: ["carrier-diagnostics", deviceId] });
  }}
  disabled={statusQuery.isFetching || usageQuery.isFetching}
>
  <RefreshCw className={cn("h-3.5 w-3.5", (statusQuery.isFetching || usageQuery.isFetching) && "animate-spin")} />
</Button>
```

### Panel Wrapper

Follow the existing panel pattern:
```tsx
<div className="rounded-md border border-border p-3 space-y-3">
  <div className="flex items-center justify-between">
    <div>
      <h3 className="text-sm font-medium">Carrier Integration</h3>
      {statusQuery.data?.linked && (
        <p className="text-xs text-muted-foreground">
          {statusQuery.data.carrier_name} · {statusQuery.data.device_info?.carrier_device_id}
        </p>
      )}
    </div>
    {/* Refresh button */}
  </div>

  {/* Status / Usage / Diagnostics sections */}
</div>
```

### Loading State

While queries are loading (initial), show a skeleton with 4 placeholder cards.

### Error State

If the status query errors, show:
```tsx
<div className="text-sm text-destructive">
  Failed to load carrier data. <Button variant="link" size="sm" onClick={refetch}>Retry</Button>
</div>
```

## Add to DeviceDetailPage

In `DeviceDetailPage.tsx`:

1. Import:
```tsx
import { DeviceCarrierPanel } from "./DeviceCarrierPanel";
```

2. Add to the panel stack (after DeviceConnectionPanel or DeviceHealthPanel):
```tsx
{deviceId && <DeviceCarrierPanel deviceId={deviceId} />}
```

## Verification

```bash
cd frontend && npx tsc --noEmit && npm run build
```
