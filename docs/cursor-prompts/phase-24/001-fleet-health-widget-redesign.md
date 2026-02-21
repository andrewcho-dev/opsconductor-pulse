# Fleet Health Widget Redesign

## Problem

The current Fleet Health Widget shows **averages** (avg battery, avg temp, avg RSSI). This is useless for fleet management because:
- Average battery 72% hides the 5 devices that are about to die at 8%
- Average temp 25°C hides the 3 devices overheating at 85°C
- Averages provide no actionable insight

## Goal

Redesign the Fleet Health Widget to show **distribution and problem counts** - information that actually helps customers understand their fleet and take action.

## New Design

Replace the three average gauges with **four status cards**:

```
┌─────────────────┬─────────────────┬─────────────────┬─────────────────┐
│  DEVICES ONLINE │  OPEN ALERTS    │  LOW BATTERY    │  STALE DEVICES  │
│                 │                 │                 │                 │
│     492/500     │       12        │        5        │        8        │
│      98.4%      │   ▲ 3 new/1h    │    < 20%        │   > 5 min ago   │
│   ● ● ● ● ● ○   │                 │                 │                 │
└─────────────────┴─────────────────┴─────────────────┴─────────────────┘
```

### Card 1: Devices Online
- **Main number**: Count of online devices / Total devices
- **Secondary**: Percentage
- **Visual**: Small dot array or mini bar showing online proportion
- **Color**: Green when > 95%, Yellow when 80-95%, Red when < 80%

### Card 2: Open Alerts
- **Main number**: Count of open alerts
- **Secondary**: "▲ X new in last hour" or "— No change"
- **Color**: Red when > 0, Green when 0
- **Click action**: Navigate to /app/alerts filtered to open

### Card 3: Low Battery
- **Main number**: Count of devices with battery < 20%
- **Secondary**: Threshold indicator "< 20%"
- **Color**: Red when > 0, Green when 0
- **Tooltip**: List device IDs with low battery

### Card 4: Stale Devices
- **Main number**: Count of devices not seen in > 5 minutes
- **Secondary**: Threshold indicator "> 5 min ago"
- **Color**: Yellow/Red based on count
- **Click action**: Navigate to /app/devices filtered to stale

## Backend API

The `/api/v2/devices` endpoint already returns device states. Create a new lightweight endpoint for fleet summary:

### New Endpoint: GET /api/v2/fleet/summary

```json
{
  "total_devices": 500,
  "online": 492,
  "stale": 8,
  "offline": 0,
  "alerts_open": 12,
  "alerts_new_1h": 3,
  "low_battery_count": 5,
  "low_battery_threshold": 20,
  "low_battery_devices": ["dev-023", "dev-156", "dev-289", "dev-301", "dev-445"]
}
```

**Implementation** (`services/ui_iot/routes/api_v2.py`):

```python
@router.get("/fleet/summary")
async def get_fleet_summary(request: Request, background_tasks: BackgroundTasks):
    """Fleet health summary for dashboard widget."""
    tenant_id = request.state.tenant_id
    pool = request.app.state.pool

    async with pool.acquire() as conn:
        await conn.execute("SET LOCAL ROLE pulse_app")
        await conn.execute("SELECT set_config('app.tenant_id', $1, true)", tenant_id)

        # Count devices by state
        device_counts = await conn.fetchrow("""
            SELECT
                COUNT(*) as total,
                COUNT(*) FILTER (WHERE state = 'online') as online,
                COUNT(*) FILTER (WHERE state = 'stale') as stale,
                COUNT(*) FILTER (WHERE state = 'offline') as offline
            FROM device_state
            WHERE tenant_id = $1
        """, tenant_id)

        # Count open alerts
        alert_counts = await conn.fetchrow("""
            SELECT
                COUNT(*) as open_alerts,
                COUNT(*) FILTER (WHERE created_at > NOW() - INTERVAL '1 hour') as new_1h
            FROM fleet_alert
            WHERE tenant_id = $1 AND status = 'open'
        """, tenant_id)

        # Find low battery devices
        low_battery = await conn.fetch("""
            SELECT device_id
            FROM device_state
            WHERE tenant_id = $1
              AND (state_json->>'battery_pct')::float < 20
        """, tenant_id)

    return {
        "total_devices": device_counts["total"],
        "online": device_counts["online"],
        "stale": device_counts["stale"],
        "offline": device_counts["offline"],
        "alerts_open": alert_counts["open_alerts"],
        "alerts_new_1h": alert_counts["new_1h"],
        "low_battery_count": len(low_battery),
        "low_battery_threshold": 20,
        "low_battery_devices": [r["device_id"] for r in low_battery[:10]]
    }
```

## Frontend Implementation

### File: `frontend/src/features/dashboard/widgets/FleetHealthWidget.tsx`

**Delete the current implementation** and replace with:

```tsx
import { useQuery } from "@tanstack/react-query";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Wifi, AlertTriangle, Battery, Clock } from "lucide-react";
import { apiGet } from "@/services/api/client";
import { Link } from "react-router-dom";

interface FleetSummary {
  total_devices: number;
  online: number;
  stale: number;
  offline: number;
  alerts_open: number;
  alerts_new_1h: number;
  low_battery_count: number;
  low_battery_devices: string[];
}

export function FleetHealthWidget() {
  const { data, isLoading } = useQuery({
    queryKey: ["fleet-summary"],
    queryFn: () => apiGet<FleetSummary>("/api/v2/fleet/summary"),
    refetchInterval: 10000,
  });

  if (isLoading || !data) {
    return <div className="animate-pulse h-32 bg-muted rounded-lg" />;
  }

  const onlinePct = data.total_devices > 0
    ? Math.round((data.online / data.total_devices) * 100)
    : 0;

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-lg">Fleet Health</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {/* Devices Online */}
          <StatusCard
            icon={Wifi}
            label="Online"
            value={`${data.online}/${data.total_devices}`}
            subtext={`${onlinePct}%`}
            status={onlinePct >= 95 ? "success" : onlinePct >= 80 ? "warning" : "error"}
          />

          {/* Open Alerts */}
          <Link to="/app/alerts?status=open">
            <StatusCard
              icon={AlertTriangle}
              label="Open Alerts"
              value={data.alerts_open.toString()}
              subtext={data.alerts_new_1h > 0 ? `▲ ${data.alerts_new_1h} new/1h` : "—"}
              status={data.alerts_open > 0 ? "error" : "success"}
            />
          </Link>

          {/* Low Battery */}
          <StatusCard
            icon={Battery}
            label="Low Battery"
            value={data.low_battery_count.toString()}
            subtext="< 20%"
            status={data.low_battery_count > 0 ? "warning" : "success"}
            tooltip={data.low_battery_devices.join(", ")}
          />

          {/* Stale Devices */}
          <Link to="/app/devices?state=stale">
            <StatusCard
              icon={Clock}
              label="Stale"
              value={data.stale.toString()}
              subtext="> 5 min"
              status={data.stale > 0 ? "warning" : "success"}
            />
          </Link>
        </div>
      </CardContent>
    </Card>
  );
}

interface StatusCardProps {
  icon: React.ElementType;
  label: string;
  value: string;
  subtext: string;
  status: "success" | "warning" | "error";
  tooltip?: string;
}

function StatusCard({ icon: Icon, label, value, subtext, status, tooltip }: StatusCardProps) {
  const colors = {
    success: "text-green-600 dark:text-green-400",
    warning: "text-yellow-600 dark:text-yellow-400",
    error: "text-red-600 dark:text-red-400",
  };

  const bgColors = {
    success: "bg-green-50 dark:bg-green-950",
    warning: "bg-yellow-50 dark:bg-yellow-950",
    error: "bg-red-50 dark:bg-red-950",
  };

  return (
    <div
      className={`p-3 rounded-lg ${bgColors[status]} cursor-pointer hover:opacity-80 transition`}
      title={tooltip}
    >
      <div className="flex items-center gap-2 mb-1">
        <Icon className={`h-4 w-4 ${colors[status]}`} />
        <span className="text-xs text-muted-foreground">{label}</span>
      </div>
      <div className={`text-2xl font-bold ${colors[status]}`}>{value}</div>
      <div className="text-xs text-muted-foreground">{subtext}</div>
    </div>
  );
}
```

## Files to Modify

| File | Change |
|------|--------|
| `services/ui_iot/routes/api_v2.py` | Add `/fleet/summary` endpoint |
| `frontend/src/features/dashboard/widgets/FleetHealthWidget.tsx` | Replace with new design |
| `frontend/src/services/api/devices.ts` | Add `fetchFleetSummary()` function |

## Verification

1. Customer dashboard shows 4 status cards instead of 3 average gauges
2. Cards show counts, not averages
3. Color coding reflects fleet health (green = good, red = needs attention)
4. Click on "Open Alerts" navigates to alerts page
5. Click on "Stale" navigates to devices filtered by stale
6. Low battery tooltip shows device IDs
7. Refreshes every 10 seconds

## Why This Is Better

| Old (Averages) | New (Counts) |
|----------------|--------------|
| "Avg Battery: 72%" | "5 devices < 20% battery" |
| Hides problems | Surfaces problems |
| Not actionable | Directly actionable |
| No navigation | Click to see affected devices |
| Static gauges | Color-coded status |
