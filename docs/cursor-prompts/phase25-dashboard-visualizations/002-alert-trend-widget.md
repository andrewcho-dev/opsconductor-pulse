# Phase 25.2: Alert Trend Widget

## Task

Create a widget showing alert count over the last 24 hours as a time-series chart.

## Backend First: Add Alert History Endpoint

The frontend needs historical alert counts. Add endpoint to `services/ui_iot/routes/api_v2.py`:

```python
@router.get("/alerts/trend")
async def get_alert_trend(
    request: Request,
    hours: int = Query(24, ge=1, le=168),
):
    """
    Get hourly alert counts for the last N hours.
    Returns [{hour: ISO timestamp, opened: count, closed: count}, ...]
    """
    pool = await get_pool()
    tenant_id = request.state.tenant_id

    async with pool.acquire() as conn:
        # Set tenant context for RLS
        await conn.execute("SELECT set_config('app.tenant_id', $1, true)", tenant_id)

        rows = await conn.fetch("""
            WITH hours AS (
                SELECT generate_series(
                    date_trunc('hour', now() - interval '1 hour' * $1),
                    date_trunc('hour', now()),
                    interval '1 hour'
                ) AS hour
            ),
            opened AS (
                SELECT date_trunc('hour', created_at) AS hour, COUNT(*) AS cnt
                FROM fleet_alert
                WHERE created_at >= now() - interval '1 hour' * $1
                GROUP BY 1
            ),
            closed AS (
                SELECT date_trunc('hour', closed_at) AS hour, COUNT(*) AS cnt
                FROM fleet_alert
                WHERE closed_at >= now() - interval '1 hour' * $1
                GROUP BY 1
            )
            SELECT
                h.hour,
                COALESCE(o.cnt, 0) AS opened,
                COALESCE(c.cnt, 0) AS closed
            FROM hours h
            LEFT JOIN opened o ON o.hour = h.hour
            LEFT JOIN closed c ON c.hour = h.hour
            ORDER BY h.hour
        """, hours)

    return {
        "trend": [
            {"hour": row["hour"].isoformat(), "opened": row["opened"], "closed": row["closed"]}
            for row in rows
        ]
    }
```

## Frontend: API Function

Add to `frontend/src/services/api/alerts.ts`:

```typescript
export interface AlertTrendPoint {
  hour: string;
  opened: number;
  closed: number;
}

export async function fetchAlertTrend(hours = 24): Promise<{ trend: AlertTrendPoint[] }> {
  const res = await apiClient.get(`/alerts/trend?hours=${hours}`);
  return res.data;
}
```

## Frontend: Create Widget

Create `frontend/src/features/dashboard/widgets/AlertTrendWidget.tsx`:

```typescript
import { memo } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { useQuery } from "@tanstack/react-query";
import { fetchAlertTrend } from "@/services/api/alerts";
import { UPlotChart } from "@/lib/charts/UPlotChart";
import { TrendingUp } from "lucide-react";
import type uPlot from "uplot";

function AlertTrendWidgetInner() {
  const { data, isLoading } = useQuery({
    queryKey: ["alert-trend", 24],
    queryFn: () => fetchAlertTrend(24),
    refetchInterval: 60000, // refresh every minute
  });

  const chartData = data?.trend || [];

  // Convert to uPlot format: [timestamps[], opened[], closed[]]
  const uplotData: uPlot.AlignedData = [
    chartData.map((p) => new Date(p.hour).getTime() / 1000),
    chartData.map((p) => p.opened),
    chartData.map((p) => p.closed),
  ];

  const options: Omit<uPlot.Options, "width" | "height"> = {
    scales: { x: { time: true }, y: {} },
    axes: [
      { stroke: "#71717a", grid: { stroke: "#27272a" } },
      { stroke: "#71717a", grid: { stroke: "#27272a" }, size: 50 },
    ],
    series: [
      {},
      { label: "Opened", stroke: "#ef4444", width: 2, points: { show: false } },
      { label: "Closed", stroke: "#22c55e", width: 2, points: { show: false } },
    ],
    legend: { show: true },
  };

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <TrendingUp className="h-4 w-4" />
            Alert Trend (24h)
          </CardTitle>
        </CardHeader>
        <CardContent>
          <Skeleton className="h-[200px]" />
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-base">
          <TrendingUp className="h-4 w-4" />
          Alert Trend (24h)
        </CardTitle>
      </CardHeader>
      <CardContent>
        {chartData.length === 0 ? (
          <div className="h-[200px] flex items-center justify-center text-muted-foreground">
            No alert data
          </div>
        ) : (
          <UPlotChart options={options} data={uplotData} height={200} />
        )}
      </CardContent>
    </Card>
  );
}

export const AlertTrendWidget = memo(AlertTrendWidgetInner);
```

## Update Widget Index

Add to `frontend/src/features/dashboard/widgets/index.ts`:

```typescript
export { AlertTrendWidget } from "./AlertTrendWidget";
```

## Verification

```bash
# Backend
cd /home/opsconductor/simcloud/services/ui_iot && python3 -c "from routes.api_v2 import router; print('OK')"

# Frontend
cd /home/opsconductor/simcloud/frontend && npm run build
```

## Files

| Action | File |
|--------|------|
| MODIFY | `services/ui_iot/routes/api_v2.py` |
| MODIFY | `frontend/src/services/api/alerts.ts` |
| CREATE | `frontend/src/features/dashboard/widgets/AlertTrendWidget.tsx` |
| MODIFY | `frontend/src/features/dashboard/widgets/index.ts` |
