# Phase 29.11: Dashboard with Real-Time Charts

## Task

Replace static metric cards with sparkline charts showing historical trends. Charts update in real-time with each refresh.

---

## Create Sparkline Chart Component

**File:** `frontend/src/features/operator/components/SparklineChart.tsx`

```typescript
import { useMemo } from "react";
import { useTheme } from "@/stores/ui-store";

interface SparklineChartProps {
  data: { time: string; value: number }[];
  height?: number;
  width?: number;
  color?: string;
  showArea?: boolean;
  showLastValue?: boolean;
  unit?: string;
  label?: string;
}

export function SparklineChart({
  data,
  height = 40,
  width = 120,
  color,
  showArea = true,
  showLastValue = true,
  unit = "",
  label,
}: SparklineChartProps) {
  const theme = useTheme();
  const isDark = theme === "dark" || (theme === "system" && window.matchMedia("(prefers-color-scheme: dark)").matches);

  const chartColor = color || (isDark ? "#60a5fa" : "#3b82f6");
  const areaColor = color || (isDark ? "rgba(96, 165, 250, 0.2)" : "rgba(59, 130, 246, 0.2)");

  const { path, areaPath, minValue, maxValue, lastValue } = useMemo(() => {
    if (!data || data.length === 0) {
      return { path: "", areaPath: "", minValue: 0, maxValue: 0, lastValue: 0 };
    }

    const values = data.map((d) => d.value);
    const min = Math.min(...values);
    const max = Math.max(...values);
    const range = max - min || 1;

    const padding = 2;
    const chartWidth = width - padding * 2;
    const chartHeight = height - padding * 2;

    const points = data.map((d, i) => {
      const x = padding + (i / (data.length - 1)) * chartWidth;
      const y = padding + chartHeight - ((d.value - min) / range) * chartHeight;
      return { x, y };
    });

    // Line path
    const linePath = points
      .map((p, i) => (i === 0 ? `M ${p.x} ${p.y}` : `L ${p.x} ${p.y}`))
      .join(" ");

    // Area path (closed polygon)
    const areaPathStr =
      linePath +
      ` L ${points[points.length - 1].x} ${height - padding}` +
      ` L ${padding} ${height - padding} Z`;

    return {
      path: linePath,
      areaPath: areaPathStr,
      minValue: min,
      maxValue: max,
      lastValue: values[values.length - 1],
    };
  }, [data, width, height]);

  if (!data || data.length === 0) {
    return (
      <div
        className="flex items-center justify-center text-muted-foreground text-xs"
        style={{ width, height }}
      >
        No data
      </div>
    );
  }

  return (
    <div className="flex flex-col">
      {label && (
        <span className="text-xs text-muted-foreground mb-1">{label}</span>
      )}
      <div className="flex items-end gap-2">
        <svg width={width} height={height} className="overflow-visible">
          {showArea && (
            <path d={areaPath} fill={areaColor} />
          )}
          <path
            d={path}
            fill="none"
            stroke={chartColor}
            strokeWidth={1.5}
            strokeLinecap="round"
            strokeLinejoin="round"
          />
          {/* Last point dot */}
          {data.length > 0 && (
            <circle
              cx={width - 2}
              cy={
                2 +
                (height - 4) -
                ((lastValue - minValue) / (maxValue - minValue || 1)) *
                  (height - 4)
              }
              r={3}
              fill={chartColor}
            />
          )}
        </svg>
        {showLastValue && (
          <span className="text-lg font-semibold tabular-nums">
            {typeof lastValue === "number"
              ? lastValue.toLocaleString(undefined, { maximumFractionDigits: 1 })
              : lastValue}
            {unit && <span className="text-xs text-muted-foreground ml-0.5">{unit}</span>}
          </span>
        )}
      </div>
    </div>
  );
}
```

---

## Create Metric Chart Card Component

**File:** `frontend/src/features/operator/components/MetricChartCard.tsx`

```typescript
import { useQuery } from "@tanstack/react-query";
import { Card, CardContent } from "@/components/ui/card";
import { SparklineChart } from "./SparklineChart";
import { fetchMetricHistory } from "@/services/api/system";
import { TrendingUp, TrendingDown, Minus } from "lucide-react";

interface MetricChartCardProps {
  title: string;
  metric: string;
  unit?: string;
  icon?: React.ElementType;
  color?: string;
  minutes?: number;
  refreshInterval?: number;
}

export function MetricChartCard({
  title,
  metric,
  unit = "",
  icon: Icon,
  color,
  minutes = 15,
  refreshInterval = 10000,
}: MetricChartCardProps) {
  const { data, isLoading } = useQuery({
    queryKey: ["metric-history", metric, minutes],
    queryFn: () => fetchMetricHistory(metric, minutes),
    refetchInterval: refreshInterval,
  });

  // Calculate trend
  const trend = useMemo(() => {
    if (!data?.points || data.points.length < 2) return null;

    const recent = data.points.slice(-6); // Last 30 seconds
    const older = data.points.slice(-12, -6); // Previous 30 seconds

    if (recent.length === 0 || older.length === 0) return null;

    const recentAvg = recent.reduce((a, b) => a + b.value, 0) / recent.length;
    const olderAvg = older.reduce((a, b) => a + b.value, 0) / older.length;

    const change = ((recentAvg - olderAvg) / (olderAvg || 1)) * 100;

    if (Math.abs(change) < 5) return { direction: "flat", change: 0 };
    return {
      direction: change > 0 ? "up" : "down",
      change: Math.abs(change).toFixed(0),
    };
  }, [data?.points]);

  return (
    <Card>
      <CardContent className="p-4">
        <div className="flex items-start justify-between mb-2">
          <div className="flex items-center gap-2 text-muted-foreground">
            {Icon && <Icon className="h-4 w-4" />}
            <span className="text-sm font-medium">{title}</span>
          </div>
          {trend && (
            <div
              className={`flex items-center gap-1 text-xs ${
                trend.direction === "up"
                  ? "text-green-600 dark:text-green-400"
                  : trend.direction === "down"
                  ? "text-red-600 dark:text-red-400"
                  : "text-muted-foreground"
              }`}
            >
              {trend.direction === "up" && <TrendingUp className="h-3 w-3" />}
              {trend.direction === "down" && <TrendingDown className="h-3 w-3" />}
              {trend.direction === "flat" && <Minus className="h-3 w-3" />}
              {trend.change > 0 && <span>{trend.change}%</span>}
            </div>
          )}
        </div>

        {isLoading ? (
          <div className="h-10 flex items-center justify-center text-muted-foreground text-sm">
            Loading...
          </div>
        ) : (
          <SparklineChart
            data={data?.points || []}
            width={200}
            height={50}
            color={color}
            unit={unit}
          />
        )}

        <div className="text-xs text-muted-foreground mt-2">
          Last {minutes} minutes
        </div>
      </CardContent>
    </Card>
  );
}
```

---

## Update System Dashboard

**File:** `frontend/src/features/operator/SystemDashboard.tsx`

Replace the static MetricCard components with MetricChartCard:

```typescript
import { MetricChartCard } from "./components/MetricChartCard";
import {
  Activity,
  Upload,
  Send,
  AlertTriangle,
  Database,
  Radio,
  Bell,
} from "lucide-react";

// In the metrics section, replace the grid of MetricCards with:
<div className="grid grid-cols-2 md:grid-cols-4 gap-4">
  <MetricChartCard
    title="Ingest Rate"
    metric="messages_written"
    unit="/s"
    icon={Activity}
    color="#22c55e"
    minutes={15}
    refreshInterval={refreshInterval}
  />
  <MetricChartCard
    title="Queue Depth"
    metric="queue_depth"
    icon={Upload}
    color="#3b82f6"
    minutes={15}
    refreshInterval={refreshInterval}
  />
  <MetricChartCard
    title="Pending Deliveries"
    metric="jobs_pending"
    icon={Send}
    color="#f59e0b"
    minutes={15}
    refreshInterval={refreshInterval}
  />
  <MetricChartCard
    title="Failed Deliveries"
    metric="jobs_failed"
    icon={AlertTriangle}
    color="#ef4444"
    minutes={15}
    refreshInterval={refreshInterval}
  />
</div>

{/* Additional charts row */}
<div className="grid grid-cols-2 md:grid-cols-4 gap-4">
  <MetricChartCard
    title="DB Connections"
    metric="connections"
    icon={Database}
    color="#8b5cf6"
    minutes={15}
    refreshInterval={refreshInterval}
  />
  <MetricChartCard
    title="Devices Online"
    metric="devices_online"
    icon={Radio}
    color="#22c55e"
    minutes={15}
    refreshInterval={refreshInterval}
  />
  <MetricChartCard
    title="Devices Stale"
    metric="devices_stale"
    icon={Radio}
    color="#f59e0b"
    minutes={15}
    refreshInterval={refreshInterval}
  />
  <MetricChartCard
    title="Open Alerts"
    metric="alerts_open"
    icon={Bell}
    color="#ef4444"
    minutes={15}
    refreshInterval={refreshInterval}
  />
</div>
```

---

## Add Larger Time-Range Charts

For key metrics, add a larger chart section:

```typescript
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer } from "recharts";

// Create a larger chart component
function MetricTimeSeriesChart({
  title,
  metric,
  minutes = 60,
  color = "#3b82f6",
}: {
  title: string;
  metric: string;
  minutes?: number;
  color?: string;
}) {
  const { data } = useQuery({
    queryKey: ["metric-history", metric, minutes],
    queryFn: () => fetchMetricHistory(metric, minutes),
    refetchInterval: refreshInterval,
  });

  const chartData = useMemo(() => {
    if (!data?.points) return [];
    return data.points.map((p) => ({
      time: new Date(p.time).toLocaleTimeString(),
      value: p.value,
    }));
  }, [data?.points]);

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-lg">{title}</CardTitle>
      </CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={200}>
          <LineChart data={chartData}>
            <XAxis
              dataKey="time"
              tick={{ fontSize: 10 }}
              interval="preserveStartEnd"
            />
            <YAxis tick={{ fontSize: 10 }} width={40} />
            <Tooltip />
            <Line
              type="monotone"
              dataKey="value"
              stroke={color}
              strokeWidth={2}
              dot={false}
            />
          </LineChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
}

// Add to dashboard:
<div className="grid grid-cols-1 md:grid-cols-2 gap-6">
  <MetricTimeSeriesChart
    title="Ingest Rate (Last Hour)"
    metric="messages_written"
    minutes={60}
    color="#22c55e"
  />
  <MetricTimeSeriesChart
    title="Queue Depth (Last Hour)"
    metric="queue_depth"
    minutes={60}
    color="#3b82f6"
  />
</div>
```

---

## Install Recharts (if not already)

```bash
cd /home/opsconductor/simcloud/frontend
npm install recharts
```

---

## Rebuild

```bash
cd /home/opsconductor/simcloud/frontend && npm run build
cp -r dist/* ../services/ui_iot/spa/
cd ../compose && docker compose restart ui
```

---

## Files

| Action | File |
|--------|------|
| CREATE | `frontend/src/features/operator/components/SparklineChart.tsx` |
| CREATE | `frontend/src/features/operator/components/MetricChartCard.tsx` |
| MODIFY | `frontend/src/features/operator/SystemDashboard.tsx` |
