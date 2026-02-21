# Task 004 -- Fleet Health Score

## Goal

Add a fleet health score endpoint and a circular gauge widget on the dashboard. The score provides a single at-a-glance metric: what percentage of the fleet is operational and alert-free.

**Formula:**
`score = ((devices_online - devices_with_critical_alerts) / total_devices) * 100`

Clamped to 0-100. Returns 100 if total_devices is 0.

---

## 1. Backend -- New Endpoint

### 1a. Add endpoint to routes/devices.py

**File:** `services/ui_iot/routes/devices.py`

This file already has a router for `/customer` prefix. Add the fleet health endpoint at the end of the file:

```python
@router.get("/fleet/health")
@limiter.limit(CUSTOMER_RATE_LIMIT)
async def get_fleet_health(
    request: Request,
    response: Response,
    pool=Depends(get_db_pool),
):
    """
    Returns a fleet health score: percentage of online devices not affected by critical alerts.

    Score = ((online_devices - devices_with_critical_alerts) / total_devices) * 100
    Clamped to [0, 100]. Returns 100 if total_devices is 0.
    """
    tenant_id = get_tenant_id()
    try:
        async with tenant_connection(pool, tenant_id) as conn:
            # Total active devices
            total_devices = await conn.fetchval(
                """
                SELECT COUNT(*)
                FROM device_registry
                WHERE tenant_id = $1 AND status = 'ACTIVE'
                """,
                tenant_id,
            )
            total_devices = int(total_devices or 0)

            # Online devices (have recent heartbeat in device_state)
            online_devices = await conn.fetchval(
                """
                SELECT COUNT(*)
                FROM device_state
                WHERE tenant_id = $1 AND status = 'ONLINE'
                """,
                tenant_id,
            )
            online_devices = int(online_devices or 0)

            # Distinct devices with at least one OPEN critical alert (severity >= 5)
            critical_alert_devices = await conn.fetchval(
                """
                SELECT COUNT(DISTINCT device_id)
                FROM fleet_alert
                WHERE tenant_id = $1
                  AND status IN ('OPEN', 'ACKNOWLEDGED')
                  AND severity >= 5
                """,
                tenant_id,
            )
            critical_alert_devices = int(critical_alert_devices or 0)

    except Exception:
        logger.exception("Failed to compute fleet health score")
        raise HTTPException(status_code=500, detail="Internal server error")

    if total_devices == 0:
        score = 100.0
    else:
        raw_score = ((online_devices - critical_alert_devices) / total_devices) * 100
        score = max(0.0, min(100.0, round(raw_score, 1)))

    return {
        "score": score,
        "total_devices": total_devices,
        "online": online_devices,
        "critical_alerts": critical_alert_devices,
        "calculated_at": datetime.now(timezone.utc).isoformat(),
    }
```

Make sure `datetime`, `timezone` are imported at the top of the file. They should already be available via the wildcard import from `routes.customer`, but verify. Also ensure `CUSTOMER_RATE_LIMIT` is accessible (it is defined in `routes/customer.py` and imported via `from routes.customer import *`).

**Note:** The `limiter` object is also available from `routes.customer`. If not, define it or import it. Check the existing patterns in `routes/devices.py` -- other endpoints in this file already use `@limiter.limit(CUSTOMER_RATE_LIMIT)`.

---

## 2. Frontend -- API Client

### 2a. Add API function

**File:** `frontend/src/services/api/devices.ts`

Add at the end of the file:

```typescript
export interface FleetHealthResponse {
  score: number;
  total_devices: number;
  online: number;
  critical_alerts: number;
  calculated_at: string;
}

export async function fetchFleetHealth(): Promise<FleetHealthResponse> {
  return apiGet("/customer/fleet/health");
}
```

Ensure `apiGet` is imported at the top of the file (it should already be).

---

## 3. Frontend -- Fleet Health Widget

### 3a. Create the widget component

**File:** `frontend/src/features/dashboard/widgets/FleetHealthWidget.tsx`

Create a new file:

```tsx
import { useQuery } from "@tanstack/react-query";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { fetchFleetHealth } from "@/services/api/devices";

function scoreColor(score: number): string {
  if (score > 80) return "text-green-500";
  if (score >= 50) return "text-yellow-500";
  return "text-red-500";
}

function strokeColor(score: number): string {
  if (score > 80) return "stroke-green-500";
  if (score >= 50) return "stroke-yellow-500";
  return "stroke-red-500";
}

function trackColor(score: number): string {
  if (score > 80) return "stroke-green-500/20";
  if (score >= 50) return "stroke-yellow-500/20";
  return "stroke-red-500/20";
}

export function FleetHealthWidget() {
  const { data, isLoading } = useQuery({
    queryKey: ["fleet-health"],
    queryFn: fetchFleetHealth,
    refetchInterval: 30000,
  });

  const score = data?.score ?? 0;
  const total = data?.total_devices ?? 0;
  const online = data?.online ?? 0;
  const critical = data?.critical_alerts ?? 0;
  const healthy = Math.max(0, online - critical);

  // SVG circular gauge parameters
  const size = 120;
  const strokeWidth = 10;
  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  const progress = (score / 100) * circumference;
  const dashOffset = circumference - progress;

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Fleet Health</CardTitle>
        </CardHeader>
        <CardContent className="flex items-center justify-center py-8">
          <div className="h-[120px] w-[120px] animate-pulse rounded-full bg-muted" />
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Fleet Health</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="flex items-center gap-6">
          {/* Circular gauge */}
          <div className="relative flex-shrink-0">
            <svg
              width={size}
              height={size}
              viewBox={`0 0 ${size} ${size}`}
              className="-rotate-90"
            >
              {/* Background track */}
              <circle
                cx={size / 2}
                cy={size / 2}
                r={radius}
                fill="none"
                strokeWidth={strokeWidth}
                className={trackColor(score)}
              />
              {/* Progress arc */}
              <circle
                cx={size / 2}
                cy={size / 2}
                r={radius}
                fill="none"
                strokeWidth={strokeWidth}
                strokeLinecap="round"
                strokeDasharray={circumference}
                strokeDashoffset={dashOffset}
                className={`${strokeColor(score)} transition-all duration-700`}
              />
            </svg>
            {/* Score text centered in the circle */}
            <div className="absolute inset-0 flex flex-col items-center justify-center">
              <span className={`text-2xl font-bold ${scoreColor(score)}`}>
                {score}%
              </span>
            </div>
          </div>

          {/* Text details */}
          <div className="space-y-1 text-sm">
            <div>
              <span className="font-medium">{healthy}</span>
              <span className="text-muted-foreground">/{total} devices healthy</span>
            </div>
            <div className="text-xs text-muted-foreground">
              {online} online, {critical} with critical alerts
            </div>
            {score <= 50 && (
              <div className="text-xs font-medium text-red-500">
                Fleet health is degraded
              </div>
            )}
            {score > 50 && score <= 80 && (
              <div className="text-xs font-medium text-yellow-500">
                Some devices need attention
              </div>
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
```

### 3b. Export from widgets index

Check if there is a `frontend/src/features/dashboard/widgets/index.ts` barrel export file. If so, add:

```typescript
export { FleetHealthWidget } from "./FleetHealthWidget";
```

If there is no index file, import directly in DashboardPage.

### 3c. Add widget to DashboardPage

**File:** `frontend/src/features/dashboard/DashboardPage.tsx`

Add import at the top:

```typescript
import { FleetHealthWidget } from "./widgets/FleetHealthWidget";
```

Or if the widgets directory uses a barrel export that already exports `AlertTrendWidget` and `DeviceStatusWidget`:

```typescript
import { AlertTrendWidget, DeviceStatusWidget, FleetHealthWidget } from "./widgets";
```

Add the widget to the dashboard layout. Place it in a prominent position -- in the first grid row, alongside the existing FleetKpiStrip. Add it before the `<div className="grid gap-6 lg:grid-cols-2">` that contains Active Alerts and Device Status (around line 167):

```tsx
      <div className="grid gap-6 lg:grid-cols-3">
        <div className="lg:col-span-2">
          <WidgetErrorBoundary widgetName="Fleet Uptime">
            <UptimeSummaryWidget />
          </WidgetErrorBoundary>
        </div>
        <WidgetErrorBoundary widgetName="Fleet Health">
          <FleetHealthWidget />
        </WidgetErrorBoundary>
      </div>
```

This replaces the existing standalone UptimeSummaryWidget section (lines 163-165). The uptime widget gets 2/3 width and the health gauge gets 1/3.

**Before (lines 163-165):**
```tsx
      <WidgetErrorBoundary widgetName="Fleet Uptime">
        <UptimeSummaryWidget />
      </WidgetErrorBoundary>
```

**After:**
```tsx
      <div className="grid gap-6 lg:grid-cols-3">
        <div className="lg:col-span-2">
          <WidgetErrorBoundary widgetName="Fleet Uptime">
            <UptimeSummaryWidget />
          </WidgetErrorBoundary>
        </div>
        <WidgetErrorBoundary widgetName="Fleet Health">
          <FleetHealthWidget />
        </WidgetErrorBoundary>
      </div>
```

Import `WidgetErrorBoundary` is already present. Import `FleetHealthWidget` as shown above.

---

## 4. Verification

```bash
# 1. No migration needed for this task (only backend code + frontend)

# 2. Restart UI service
docker compose restart ui

# 3. Test endpoint directly
curl -s http://localhost:3000/customer/fleet/health \
  -H "Authorization: Bearer $TOKEN" | jq .

# Expected response shape:
# {
#   "score": 85.7,
#   "total_devices": 14,
#   "online": 12,
#   "critical_alerts": 0,
#   "calculated_at": "2026-02-16T10:30:00.000000+00:00"
# }

# 4. Test edge cases:
# - No devices: score should be 100
# - All devices offline: score should be 0
# - Some critical alerts: score should reflect deduction

# 5. Frontend build
cd frontend && npm run build

# 6. Visual check:
# - Navigate to dashboard
# - Verify circular gauge widget appears in the top section
# - Green gauge for score > 80
# - Yellow gauge for score 50-80
# - Red gauge for score < 50
# - Text shows "X/Y devices healthy"
# - Widget auto-refreshes every 30 seconds
```

---

## Commit

```
feat(dashboard): add fleet health score endpoint and gauge widget

- Backend: GET /customer/fleet/health returns score, online, critical counts
- Frontend: FleetHealthWidget with circular SVG gauge (green/yellow/red)
- Dashboard: widget placed alongside uptime summary in 3-column grid
```
