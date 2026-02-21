# 002 -- Ad-Hoc Telemetry Analytics

## Goal

Create a full analytics page at `/analytics` with a backend query engine and frontend query builder. Users select a metric, aggregation function, time range, and optional grouping, then run the query to see a time-series chart, summary stats, and raw data table. Results can be exported as CSV.

## Backend

### 1. Create `services/ui_iot/routes/analytics.py`

This is a new route file. Follow the same patterns as `routes/devices.py` and `routes/customer.py`.

```python
"""Ad-hoc telemetry analytics -- query builder, aggregation, CSV export."""

import csv
import io
from datetime import datetime, timezone
from typing import Optional, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from middleware.auth import JWTBearer
from middleware.tenant import inject_tenant_context, get_tenant_id, require_customer
from db.pool import tenant_connection
from dependencies import get_db_pool
from shared.logging import get_logger

logger = get_logger("pulse.analytics")

router = APIRouter(
    prefix="/customer/analytics",
    tags=["analytics"],
    dependencies=[
        Depends(JWTBearer()),
        Depends(inject_tenant_context),
        Depends(require_customer),
    ],
)


# --- Request / Response Models ---

class AnalyticsQueryRequest(BaseModel):
    metric: str = Field(..., min_length=1, max_length=100)
    aggregation: Literal["avg", "min", "max", "p95", "sum", "count"] = "avg"
    time_range: Literal["1h", "6h", "24h", "7d", "30d"] = "24h"
    group_by: Literal["device", "site", "group"] | None = None
    device_ids: list[str] | None = None
    group_id: str | None = None
    bucket_size: str | None = None  # e.g. "5 minutes", "1 hour"


class AnalyticsPoint(BaseModel):
    time: str
    value: float | None


class AnalyticsSeries(BaseModel):
    label: str
    points: list[AnalyticsPoint]


class AnalyticsSummary(BaseModel):
    min: float | None
    max: float | None
    avg: float | None
    total_points: int


class AnalyticsQueryResponse(BaseModel):
    series: list[AnalyticsSeries]
    summary: AnalyticsSummary


# --- Time range / bucket mapping ---

TIME_RANGE_MAP: dict[str, tuple[str, str]] = {
    "1h":  ("1 hour",  "1 minute"),
    "6h":  ("6 hours", "5 minutes"),
    "24h": ("24 hours", "15 minutes"),
    "7d":  ("7 days",  "1 hour"),
    "30d": ("30 days", "6 hours"),
}

AGGREGATION_SQL: dict[str, str] = {
    "avg":   "AVG((metrics->>$2)::numeric)",
    "min":   "MIN((metrics->>$2)::numeric)",
    "max":   "MAX((metrics->>$2)::numeric)",
    "sum":   "SUM((metrics->>$2)::numeric)",
    "count": "COUNT(*)",
    "p95":   "percentile_cont(0.95) WITHIN GROUP (ORDER BY (metrics->>$2)::numeric)",
}


# --- Endpoints ---

@router.get("/metrics")
async def list_available_metrics(pool=Depends(get_db_pool)):
    """Return distinct metric names from recent telemetry for this tenant."""
    tenant_id = get_tenant_id()
    try:
        async with tenant_connection(pool, tenant_id) as conn:
            rows = await conn.fetch(
                """
                SELECT DISTINCT jsonb_object_keys(metrics) AS metric_name
                FROM telemetry
                WHERE tenant_id = $1
                  AND time > now() - interval '7 days'
                ORDER BY metric_name
                """,
                tenant_id,
            )
    except Exception:
        logger.exception("Failed to list analytics metrics")
        raise HTTPException(status_code=500, detail="Internal server error")

    return {"metrics": [row["metric_name"] for row in rows]}


@router.post("/query", response_model=AnalyticsQueryResponse)
async def run_analytics_query(
    body: AnalyticsQueryRequest,
    pool=Depends(get_db_pool),
):
    """Execute an ad-hoc analytics query with time_bucket aggregation."""
    tenant_id = get_tenant_id()

    lookback, default_bucket = TIME_RANGE_MAP.get(
        body.time_range, TIME_RANGE_MAP["24h"]
    )
    bucket = body.bucket_size or default_bucket

    agg_expr = AGGREGATION_SQL.get(body.aggregation)
    if not agg_expr:
        raise HTTPException(status_code=400, detail="Invalid aggregation")

    # Build the WHERE clause dynamically
    # $1 = bucket interval, $2 = metric name, $3 = tenant_id, $4 = lookback interval
    conditions = [
        "tenant_id = $3",
        "time > now() - $4::interval",
        "metrics ? $2",
    ]
    params: list = [bucket, body.metric, tenant_id, lookback]
    param_idx = 5

    # Filter by device_ids
    if body.device_ids and len(body.device_ids) > 0:
        conditions.append(f"device_id = ANY(${param_idx}::text[])")
        params.append(body.device_ids)
        param_idx += 1

    # Filter by group membership
    if body.group_id:
        conditions.append(
            f"""device_id IN (
                SELECT device_id FROM device_group_members
                WHERE tenant_id = $3 AND group_id = ${param_idx}
            )"""
        )
        params.append(body.group_id)
        param_idx += 1

    where_clause = " AND ".join(conditions)

    # Build GROUP BY / label based on group_by
    if body.group_by == "device":
        group_col = "device_id"
        label_expr = "device_id"
    elif body.group_by == "site":
        group_col = "site_id"
        label_expr = "COALESCE(site_id, 'unknown')"
    elif body.group_by == "group":
        # For group_by=group, we need to join device_group_members
        # This is more complex -- fall back to device grouping
        group_col = "device_id"
        label_expr = "device_id"
    else:
        group_col = None
        label_expr = "'all'"

    if group_col:
        query = f"""
            SELECT
                {label_expr} AS label,
                time_bucket($1::interval, time) AS bucket,
                {agg_expr} AS agg_value
            FROM telemetry
            WHERE {where_clause}
            GROUP BY label, bucket
            ORDER BY label, bucket ASC
        """
    else:
        query = f"""
            SELECT
                {label_expr} AS label,
                time_bucket($1::interval, time) AS bucket,
                {agg_expr} AS agg_value
            FROM telemetry
            WHERE {where_clause}
            GROUP BY bucket
            ORDER BY bucket ASC
        """

    try:
        async with tenant_connection(pool, tenant_id) as conn:
            rows = await conn.fetch(query, *params)
    except Exception:
        logger.exception("Analytics query failed")
        raise HTTPException(status_code=500, detail="Query execution failed")

    # Group rows into series
    series_map: dict[str, list[AnalyticsPoint]] = {}
    all_values: list[float] = []

    for row in rows:
        label = str(row["label"])
        value = float(row["agg_value"]) if row["agg_value"] is not None else None
        point = AnalyticsPoint(
            time=row["bucket"].isoformat(),
            value=value,
        )

        if label not in series_map:
            series_map[label] = []
        series_map[label].append(point)

        if value is not None:
            all_values.append(value)

    series = [
        AnalyticsSeries(label=label, points=points)
        for label, points in series_map.items()
    ]

    summary = AnalyticsSummary(
        min=round(min(all_values), 4) if all_values else None,
        max=round(max(all_values), 4) if all_values else None,
        avg=round(sum(all_values) / len(all_values), 4) if all_values else None,
        total_points=len(all_values),
    )

    return AnalyticsQueryResponse(series=series, summary=summary)


@router.get("/export")
async def export_analytics_csv(
    metric: str = Query(..., min_length=1),
    aggregation: Literal["avg", "min", "max", "p95", "sum", "count"] = Query("avg"),
    time_range: Literal["1h", "6h", "24h", "7d", "30d"] = Query("24h"),
    group_by: str | None = Query(None),
    device_ids: str | None = Query(None, description="Comma-separated device IDs"),
    group_id: str | None = Query(None),
    pool=Depends(get_db_pool),
):
    """Export analytics query results as CSV."""
    # Parse device_ids from comma-separated string
    device_id_list = (
        [d.strip() for d in device_ids.split(",") if d.strip()]
        if device_ids
        else None
    )

    # Re-use the query endpoint logic
    body = AnalyticsQueryRequest(
        metric=metric,
        aggregation=aggregation,
        time_range=time_range,
        group_by=group_by if group_by in ("device", "site", "group") else None,
        device_ids=device_id_list,
        group_id=group_id,
    )
    result = await run_analytics_query(body, pool)

    # Build CSV
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["label", "time", "value"])

    for s in result.series:
        for point in s.points:
            writer.writerow([s.label, point.time, point.value if point.value is not None else ""])

    output.seek(0)
    filename = f"analytics_{metric}_{aggregation}_{time_range}.csv"

    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
```

### 2. Register the router in `services/ui_iot/app.py`

Add the import near the top with other route imports (around line 24-45):

```python
from routes.analytics import router as analytics_router
```

Add the include_router call after the existing routers (around line 186):

```python
app.include_router(analytics_router)
```

## Frontend

### 3. Create `frontend/src/services/api/analytics.ts`

API client functions for the analytics endpoints.

```typescript
import { apiGet, apiPost } from "./client";
import keycloak from "@/services/auth/keycloak";

// Types
export type Aggregation = "avg" | "min" | "max" | "p95" | "sum" | "count";
export type TimeRange = "1h" | "6h" | "24h" | "7d" | "30d";
export type GroupBy = "device" | "site" | "group" | null;

export interface AnalyticsQueryRequest {
  metric: string;
  aggregation: Aggregation;
  time_range: TimeRange;
  group_by: GroupBy;
  device_ids?: string[];
  group_id?: string;
  bucket_size?: string;
}

export interface AnalyticsPoint {
  time: string;
  value: number | null;
}

export interface AnalyticsSeries {
  label: string;
  points: AnalyticsPoint[];
}

export interface AnalyticsSummary {
  min: number | null;
  max: number | null;
  avg: number | null;
  total_points: number;
}

export interface AnalyticsQueryResponse {
  series: AnalyticsSeries[];
  summary: AnalyticsSummary;
}

export interface AvailableMetricsResponse {
  metrics: string[];
}

// API functions

export async function fetchAvailableMetrics(): Promise<AvailableMetricsResponse> {
  return apiGet("/customer/analytics/metrics");
}

export async function runAnalyticsQuery(
  request: AnalyticsQueryRequest
): Promise<AnalyticsQueryResponse> {
  return apiPost("/customer/analytics/query", request);
}

export async function downloadAnalyticsCSV(
  request: AnalyticsQueryRequest
): Promise<void> {
  if (keycloak.authenticated) {
    await keycloak.updateToken(30);
  }

  const params = new URLSearchParams();
  params.set("metric", request.metric);
  params.set("aggregation", request.aggregation);
  params.set("time_range", request.time_range);
  if (request.group_by) params.set("group_by", request.group_by);
  if (request.device_ids && request.device_ids.length > 0) {
    params.set("device_ids", request.device_ids.join(","));
  }
  if (request.group_id) params.set("group_id", request.group_id);

  const headers: Record<string, string> = {};
  if (keycloak.token) {
    headers.Authorization = `Bearer ${keycloak.token}`;
  }

  const res = await fetch(`/customer/analytics/export?${params.toString()}`, {
    headers,
  });
  if (!res.ok) {
    throw new Error(`Export failed: ${res.status}`);
  }

  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = `analytics_${request.metric}_${request.aggregation}_${request.time_range}.csv`;
  document.body.appendChild(anchor);
  anchor.click();
  document.body.removeChild(anchor);
  URL.revokeObjectURL(url);
}
```

### 4. Create `frontend/src/features/analytics/AnalyticsPage.tsx`

The main analytics page with query builder and results visualization.

**Page Layout:**

```
+------------------------------------------+
| Analytics                    [Export CSV] |
+----------------+-------------------------+
| QUERY BUILDER  |  RESULTS                |
| (left panel)   |  +-------------------+  |
|                |  | Summary Stats Bar |  |
| Metric:  [___] |  +-------------------+  |
| Agg:     [___] |  |                   |  |
| Range:   [___] |  |   ECharts Line    |  |
| Group by:[___] |  |   Chart           |  |
| Devices: [___] |  |                   |  |
|                |  +-------------------+  |
| [Run Query]    |  |                   |  |
|                |  |   Data Table      |  |
|                |  |                   |  |
+----------------+-------------------------+
```

**Component structure:**

```tsx
import { useState, useMemo } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import {
  fetchAvailableMetrics,
  runAnalyticsQuery,
  downloadAnalyticsCSV,
} from "@/services/api/analytics";
import type {
  Aggregation,
  TimeRange,
  GroupBy,
  AnalyticsQueryRequest,
  AnalyticsQueryResponse,
} from "@/services/api/analytics";
import { fetchDevices } from "@/services/api/devices";
import { fetchDeviceGroups } from "@/services/api/devices";
import { EChartWrapper } from "@/lib/charts/EChartWrapper";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { BarChart3, Download, Play, Loader2 } from "lucide-react";

const AGGREGATION_OPTIONS: { value: Aggregation; label: string }[] = [
  { value: "avg", label: "Average" },
  { value: "min", label: "Minimum" },
  { value: "max", label: "Maximum" },
  { value: "p95", label: "95th Percentile" },
  { value: "sum", label: "Sum" },
  { value: "count", label: "Count" },
];

const TIME_RANGE_OPTIONS: { value: TimeRange; label: string }[] = [
  { value: "1h", label: "Last 1 hour" },
  { value: "6h", label: "Last 6 hours" },
  { value: "24h", label: "Last 24 hours" },
  { value: "7d", label: "Last 7 days" },
  { value: "30d", label: "Last 30 days" },
];

const GROUP_BY_OPTIONS: { value: string; label: string }[] = [
  { value: "none", label: "No grouping" },
  { value: "device", label: "By Device" },
  { value: "site", label: "By Site" },
  { value: "group", label: "By Device Group" },
];
```

**State management:**

```tsx
export default function AnalyticsPage() {
  // Query builder state
  const [metric, setMetric] = useState<string>("");
  const [aggregation, setAggregation] = useState<Aggregation>("avg");
  const [timeRange, setTimeRange] = useState<TimeRange>("24h");
  const [groupBy, setGroupBy] = useState<string>("none");
  const [selectedDeviceIds, setSelectedDeviceIds] = useState<string[]>([]);

  // Query results
  const [results, setResults] = useState<AnalyticsQueryResponse | null>(null);

  // Fetch available metrics for the dropdown
  const { data: metricsData, isLoading: metricsLoading } = useQuery({
    queryKey: ["analytics-metrics"],
    queryFn: fetchAvailableMetrics,
  });

  // Fetch devices for the device filter multi-select
  const { data: devicesData } = useQuery({
    queryKey: ["analytics-devices"],
    queryFn: () => fetchDevices({ limit: 500 }),
  });

  // Fetch device groups for the group filter
  const { data: groupsData } = useQuery({
    queryKey: ["analytics-groups"],
    queryFn: fetchDeviceGroups,
  });

  // Run query mutation
  const queryMutation = useMutation({
    mutationFn: runAnalyticsQuery,
    onSuccess: (data) => setResults(data),
  });

  const handleRunQuery = () => {
    if (!metric) return;
    const request: AnalyticsQueryRequest = {
      metric,
      aggregation,
      time_range: timeRange,
      group_by: groupBy === "none" ? null : (groupBy as GroupBy),
      device_ids: selectedDeviceIds.length > 0 ? selectedDeviceIds : undefined,
    };
    queryMutation.mutate(request);
  };

  const handleExport = async () => {
    if (!metric) return;
    try {
      await downloadAnalyticsCSV({
        metric,
        aggregation,
        time_range: timeRange,
        group_by: groupBy === "none" ? null : (groupBy as GroupBy),
        device_ids: selectedDeviceIds.length > 0 ? selectedDeviceIds : undefined,
      });
    } catch (err) {
      console.error("CSV export failed:", err);
    }
  };
```

**ECharts line chart options builder:**

```tsx
  // Build ECharts option from results
  const chartOption = useMemo(() => {
    if (!results || results.series.length === 0) return null;

    const series = results.series.map((s) => ({
      name: s.label,
      type: "line" as const,
      smooth: true,
      symbol: "circle",
      symbolSize: 4,
      data: s.points.map((p) => [p.time, p.value]),
    }));

    return {
      tooltip: {
        trigger: "axis" as const,
        axisPointer: { type: "cross" as const },
      },
      legend: {
        show: results.series.length > 1 && results.series.length <= 10,
        bottom: 0,
        type: "scroll" as const,
      },
      grid: {
        left: 60,
        right: 20,
        top: 20,
        bottom: results.series.length > 1 ? 40 : 20,
      },
      xAxis: {
        type: "time" as const,
      },
      yAxis: {
        type: "value" as const,
        name: `${aggregation}(${metric})`,
      },
      series,
    };
  }, [results, aggregation, metric]);
```

**Render the page layout using the structure above:**

- Left panel (w-80 or w-72): Query builder form with Select components for each dropdown.
- Right panel (flex-1): Results area.
- If no results yet, show an empty state: "Select a metric and run a query to see results."
- While query is running, show a Loader2 spinner on the Run Query button and a skeleton in the results area.
- If query errors, show a red alert banner with retry button.

**Summary stats bar** (show when results exist):

```tsx
{results && results.summary && (
  <div className="grid grid-cols-4 gap-4 mb-4">
    <Card>
      <CardContent className="pt-4">
        <div className="text-sm text-muted-foreground">Min</div>
        <div className="text-2xl font-bold">
          {results.summary.min?.toFixed(2) ?? "--"}
        </div>
      </CardContent>
    </Card>
    <Card>
      <CardContent className="pt-4">
        <div className="text-sm text-muted-foreground">Max</div>
        <div className="text-2xl font-bold">
          {results.summary.max?.toFixed(2) ?? "--"}
        </div>
      </CardContent>
    </Card>
    <Card>
      <CardContent className="pt-4">
        <div className="text-sm text-muted-foreground">Avg</div>
        <div className="text-2xl font-bold">
          {results.summary.avg?.toFixed(2) ?? "--"}
        </div>
      </CardContent>
    </Card>
    <Card>
      <CardContent className="pt-4">
        <div className="text-sm text-muted-foreground">Data Points</div>
        <div className="text-2xl font-bold">
          {results.summary.total_points.toLocaleString()}
        </div>
      </CardContent>
    </Card>
  </div>
)}
```

**Data table** (below chart, show when results exist):

```tsx
{results && results.series.length > 0 && (
  <Card>
    <CardHeader>
      <CardTitle className="text-sm">Raw Data</CardTitle>
    </CardHeader>
    <CardContent>
      <div className="max-h-64 overflow-auto">
        <table className="w-full text-sm">
          <thead className="sticky top-0 bg-background">
            <tr className="border-b">
              {results.series.length > 1 && (
                <th className="text-left py-2 px-2 font-medium">Label</th>
              )}
              <th className="text-left py-2 px-2 font-medium">Time</th>
              <th className="text-right py-2 px-2 font-medium">Value</th>
            </tr>
          </thead>
          <tbody>
            {results.series.flatMap((s) =>
              s.points.map((p, idx) => (
                <tr key={`${s.label}-${idx}`} className="border-b">
                  {results.series.length > 1 && (
                    <td className="py-1 px-2">{s.label}</td>
                  )}
                  <td className="py-1 px-2">
                    {new Date(p.time).toLocaleString()}
                  </td>
                  <td className="py-1 px-2 text-right font-mono">
                    {p.value?.toFixed(2) ?? "--"}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </CardContent>
  </Card>
)}
```

**Device multi-select filter:**

For the device filter, use a simple approach: a scrollable list of checkboxes inside a collapsible section. Do NOT add a third-party multi-select library. Use a `<div>` with checkboxes:

```tsx
{/* Device filter - only show when group_by is not "device" to avoid confusion */}
<div className="space-y-1">
  <label className="text-sm font-medium">Filter Devices</label>
  <div className="max-h-40 overflow-auto border rounded p-2 space-y-1">
    {devicesData?.devices.map((d) => (
      <label key={d.device_id} className="flex items-center gap-2 text-xs cursor-pointer">
        <input
          type="checkbox"
          checked={selectedDeviceIds.includes(d.device_id)}
          onChange={(e) => {
            if (e.target.checked) {
              setSelectedDeviceIds((prev) => [...prev, d.device_id]);
            } else {
              setSelectedDeviceIds((prev) =>
                prev.filter((id) => id !== d.device_id)
              );
            }
          }}
        />
        <span className="truncate">{d.device_id}</span>
      </label>
    ))}
    {(!devicesData || devicesData.devices.length === 0) && (
      <div className="text-xs text-muted-foreground">No devices found</div>
    )}
  </div>
  {selectedDeviceIds.length > 0 && (
    <Button
      variant="ghost"
      size="sm"
      className="text-xs h-6"
      onClick={() => setSelectedDeviceIds([])}
    >
      Clear selection ({selectedDeviceIds.length})
    </Button>
  )}
</div>
```

## Files to Modify

### 5. `frontend/src/app/router.tsx`

Add the import:

```tsx
import AnalyticsPage from "@/features/analytics/AnalyticsPage";
```

Add the route inside `RequireCustomer` children, after `reports`:

```tsx
{ path: "analytics", element: <AnalyticsPage /> },
```

### 6. `frontend/src/components/layout/AppSidebar.tsx`

Add `BarChart3` to the lucide-react import (if not already there):

```tsx
import {
  // ... existing ...
  BarChart3,
} from "lucide-react";
```

Add "Analytics" entry to the `customerDataNav` array. Insert it before "Reports":

```tsx
const customerDataNav: NavItem[] = [
  { label: "Telemetry / Metrics", href: "/metrics", icon: Gauge },
  { label: "Analytics", href: "/analytics", icon: BarChart3 },  // <-- ADD THIS
  { label: "Reports", href: "/reports", icon: ScrollText },
  { label: "Delivery Log", href: "/delivery-log", icon: Activity },
  { label: "Export", href: "/devices", icon: ScrollText },
];
```

## SQL Query Details

The core analytics query uses TimescaleDB `time_bucket` which is already used in the codebase (`routes/devices.py` line 717). The pattern:

```sql
SELECT
    time_bucket('15 minutes'::interval, time) AS bucket,
    AVG((metrics->>'temperature')::numeric) AS agg_value
FROM telemetry
WHERE tenant_id = $1
  AND time > now() - '24 hours'::interval
  AND metrics ? 'temperature'
GROUP BY bucket
ORDER BY bucket ASC
```

For `p95`, use PostgreSQL's ordered-set aggregate:

```sql
percentile_cont(0.95) WITHIN GROUP (ORDER BY (metrics->>'temperature')::numeric)
```

This requires PostgreSQL 9.4+ which is already in use.

For `group_by = 'device'`, add `device_id` to both SELECT and GROUP BY:

```sql
SELECT
    device_id AS label,
    time_bucket('15 minutes'::interval, time) AS bucket,
    AVG((metrics->>'temperature')::numeric) AS agg_value
FROM telemetry
WHERE tenant_id = $1
  AND time > now() - '24 hours'::interval
  AND metrics ? 'temperature'
GROUP BY label, bucket
ORDER BY label, bucket ASC
```

## Important Implementation Notes

1. **Metric dropdown population.** The `GET /customer/analytics/metrics` endpoint queries `jsonb_object_keys(metrics)` over the last 7 days. This gives us all metric names without needing a separate catalog. It may be slow on very large datasets -- if so, add `LIMIT 100` or use the metric catalog from `routes/metrics.py` instead.

2. **Parameter safety.** The metric name is passed as a parameterized value `$2` and used with `->>$2` in the SQL. This is safe from injection because asyncpg parameterizes it. Do NOT string-interpolate the metric name into SQL.

3. **The aggregation function string IS interpolated** into the SQL (from `AGGREGATION_SQL` dict). This is safe because the dict keys are validated against a Literal type, so only the 6 known functions can be used.

4. **CSV export.** The export endpoint re-uses the query logic by calling `run_analytics_query` internally. This keeps the logic DRY.

5. **ECharts time axis.** Use `xAxis: { type: "time" }` so ECharts auto-formats the time axis labels. Pass data points as `[isoString, value]` tuples.

6. **Chart height.** Give the EChartWrapper a style height of at least 350-400px for good readability: `style={{ height: 400 }}`.

7. **Loading state for query.** Use `queryMutation.isPending` to show the spinner on the Run Query button and a skeleton in the results area.

## Verification

1. Navigate to `/analytics`.
2. The metric dropdown loads with available metric names (e.g., "temperature", "battery_pct").
3. Select a metric, keep aggregation as "avg" and time range as "24h".
4. Click "Run Query".
5. A line chart appears with the time series data.
6. Summary stats bar shows min, max, avg, and total data points.
7. Raw data table below the chart shows individual time-value rows.
8. Change aggregation to "p95" and re-run -- chart updates.
9. Set group_by to "By Device" and re-run -- multiple lines appear (one per device).
10. Click "Export CSV" -- CSV file downloads with correct data.
11. Sidebar shows "Analytics" link under "Data & Integrations" group.
12. Run `cd frontend && npx tsc --noEmit` -- no type errors.
13. Run `cd services/ui_iot && python -c "from routes.analytics import router; print('OK')"` -- no import errors.

## Commit

```
feat: add analytics page with query builder, time-series chart, and CSV export
```
