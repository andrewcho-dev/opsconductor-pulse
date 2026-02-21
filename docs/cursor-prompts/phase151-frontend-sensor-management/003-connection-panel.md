# Task 003 — DeviceConnectionPanel Component

## File

Create `frontend/src/features/devices/DeviceConnectionPanel.tsx`

Then add to `DeviceDetailPage.tsx`.

## Component Design

A panel showing cellular/network connection details for the device. Displays carrier info, SIM status, data usage, and network status. Editable via a form dialog.

## Layout

```
┌─────────────────────────────────────────────────────────────┐
│  Connection                                    [Edit]       │
│                                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ Type         │  │ Carrier      │  │ Network      │      │
│  │ Cellular     │  │ Hologram     │  │ Connected ●  │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
│                                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ Plan         │  │ SIM Status   │  │ IP Address   │      │
│  │ IoT Pro 500MB│  │ Active ●     │  │ 10.176.42.101│      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
│                                                             │
│  Data Usage: ██████████░░░░ 127.4 / 500 MB (25.5%)         │
│  Billing cycle resets on the 1st                            │
│                                                             │
│  SIM ICCID: 8901260012345678901                             │
│  APN: hologram                                              │
│  Last network attach: Feb 15, 2026 10:00 AM                 │
└─────────────────────────────────────────────────────────────┘
```

## Implementation

```tsx
interface DeviceConnectionPanelProps {
  deviceId: string;
}

export function DeviceConnectionPanel({ deviceId }: DeviceConnectionPanelProps) {
  const [editOpen, setEditOpen] = useState(false);
  const queryClient = useQueryClient();

  const { data, isLoading } = useQuery({
    queryKey: ["device-connection", deviceId],
    queryFn: () => getDeviceConnection(deviceId),
    enabled: !!deviceId,
  });

  const upsertMutation = useMutation({
    mutationFn: (payload: ConnectionUpsert) => upsertDeviceConnection(deviceId, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["device-connection", deviceId] });
      toast.success("Connection updated");
      setEditOpen(false);
    },
    onError: (err: Error) => toast.error(getErrorMessage(err)),
  });

  const conn = data?.connection;
  // ... render
}
```

### Key UI Elements

**No connection record:** Show an empty state with "No connection configured" + "Set Up Connection" button.

**Connection exists — Info grid:**
Use a 3-column grid of stat cards. Each shows a label (text-xs muted) + value (text-sm font-medium).

**Data usage bar:** A simple Tailwind progress bar:
```tsx
const usagePct = conn.data_limit_mb ? (conn.data_used_mb / conn.data_limit_mb) * 100 : 0;
const barColor = usagePct > 90 ? "bg-red-500" : usagePct > 75 ? "bg-orange-500" : "bg-green-500";

<div className="space-y-1">
  <div className="flex justify-between text-xs text-muted-foreground">
    <span>Data Usage</span>
    <span>{conn.data_used_mb?.toFixed(1)} / {conn.data_limit_mb} MB ({usagePct.toFixed(1)}%)</span>
  </div>
  <div className="h-2 rounded-full bg-muted overflow-hidden">
    <div className={`h-full rounded-full ${barColor}`} style={{ width: `${Math.min(usagePct, 100)}%` }} />
  </div>
</div>
```

**Status indicators:** Use colored dots:
- `connected` / `active` → green dot
- `disconnected` / `suspended` → red dot
- `unknown` → gray dot

### Edit Dialog

Use `Dialog` with form fields matching `ConnectionUpsert`:
- Connection type (Select: cellular, ethernet, wifi, lora, satellite, other)
- Carrier name (Input)
- Plan name (Input)
- APN (Input)
- SIM ICCID (Input)
- SIM status (Select: active, suspended, deactivated, ready)
- Data limit MB (Input number)
- Billing cycle start (Input number 1-28)
- IP address (Input)
- MSISDN (Input)

Pre-populate from existing connection data. On submit: call `upsertDeviceConnection`.

## Add to DeviceDetailPage.tsx

Place after `DeviceSensorsPanel` and before `DeviceApiTokensPanel`:

```tsx
import { DeviceConnectionPanel } from "./DeviceConnectionPanel";

{deviceId && <DeviceConnectionPanel deviceId={deviceId} />}
```

## Verification

```bash
cd frontend && npx tsc --noEmit && npm run build
```
