# Task 7: Consolidate Fleet Widgets

## Context

Three widgets — `device_count`, `fleet_status`, and `health_score` — all show variations of "how is my fleet doing." They share the same underlying data (device list / fleet summary) but render differently. Users should have ONE "Fleet Overview" widget with a display mode selector instead of three separate, confusingly similar options.

## Step 1: Create FleetOverviewRenderer

**File:** `frontend/src/features/dashboard/widgets/renderers/FleetOverviewRenderer.tsx` (NEW)

This renderer consolidates all three existing fleet renderers. It reads `display_mode` from config to decide which view to show:

```tsx
import React, { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import type { WidgetRendererProps } from "../widget-registry";
import type { EChartsOption } from "echarts";
import { EChartWrapper } from "@/lib/charts/EChartWrapper";
import { fetchFleetSummary, fetchFleetHealth } from "@/services/api/devices";
import { useUIStore } from "@/stores/ui-store";

type DisplayMode = "count" | "donut" | "health";

export default function FleetOverviewRenderer({ config }: WidgetRendererProps) {
  const displayMode = (config.display_mode as DisplayMode) ?? "count";
  const decimalPrecision = (config.decimal_precision as number) ?? 0;

  // Fetch fleet data (shared across all display modes)
  const { data: summary } = useQuery({
    queryKey: ["fleet-summary"],
    queryFn: fetchFleetSummary,
    refetchInterval: 30000,
  });

  const total = (summary?.online ?? 0) + (summary?.offline ?? 0) + (summary?.STALE ?? 0);
  const online = summary?.online ?? summary?.ONLINE ?? 0;
  const offline = summary?.offline ?? summary?.OFFLINE ?? 0;
  const stale = summary?.STALE ?? 0;

  if (displayMode === "count") {
    return <CountView total={total} online={online} offline={offline} decimalPrecision={decimalPrecision} />;
  }

  if (displayMode === "donut") {
    return <DonutView total={total} online={online} stale={stale} />;
  }

  if (displayMode === "health") {
    return <HealthView config={config} decimalPrecision={decimalPrecision} />;
  }

  return <CountView total={total} online={online} offline={offline} decimalPrecision={decimalPrecision} />;
}

// --- CountView: replaces DeviceCountRenderer ---
function CountView({ total, online, offline, decimalPrecision }: {
  total: number; online: number; offline: number; decimalPrecision: number;
}) {
  const fmt = (n: number) => n.toLocaleString(undefined, { maximumFractionDigits: decimalPrecision });
  return (
    <div className="h-full flex items-center justify-between px-2">
      <div>
        <div className="text-2xl font-semibold">{fmt(total)}</div>
        <div className="text-xs text-muted-foreground">Total Devices</div>
      </div>
      <div className="text-right space-y-0.5">
        <div className="text-xs"><span className="text-green-500 font-medium">{fmt(online)}</span> online</div>
        <div className="text-xs"><span className="text-red-500 font-medium">{fmt(offline)}</span> offline</div>
      </div>
    </div>
  );
}

// --- DonutView: replaces FleetStatusRenderer ---
function DonutView({ total, online, stale }: { total: number; online: number; stale: number }) {
  const isDark = useUIStore((s) => s.theme === "dark");

  const option = useMemo<EChartsOption>(() => ({
    tooltip: { trigger: "item", formatter: "{b}: {c} ({d}%)" },
    legend: {
      bottom: 0,
      textStyle: { color: isDark ? "#a1a1aa" : "#52525b" },
    },
    series: [{
      type: "pie",
      radius: ["50%", "70%"],
      center: ["50%", "45%"],
      avoidLabelOverlap: false,
      itemStyle: { borderRadius: 4, borderColor: isDark ? "#18181b" : "#e4e4e7", borderWidth: 2 },
      label: {
        show: true,
        position: "center",
        formatter: () => `${total}\nDevices`,
        fontSize: 16,
        fontWeight: "bold",
        color: isDark ? "#fafafa" : "#18181b",
        lineHeight: 22,
      },
      labelLine: { show: false },
      data: [
        { value: online, name: "Online", itemStyle: { color: isDark ? "#22c55e" : "#16a34a" } },
        { value: stale, name: "Stale", itemStyle: { color: isDark ? "#f97316" : "#ea580c" } },
      ],
    }],
  }), [total, online, stale, isDark]);

  return (
    <div className="h-full w-full min-h-[100px]">
      <EChartWrapper option={option} style={{ width: "100%", height: "100%" }} />
    </div>
  );
}

// --- HealthView: replaces HealthScoreRenderer ---
function HealthView({ config, decimalPrecision }: { config: Record<string, unknown>; decimalPrecision: number }) {
  const { data } = useQuery({
    queryKey: ["fleet-health"],
    queryFn: fetchFleetHealth,
    refetchInterval: 30000,
  });

  const total = data?.total ?? 0;
  const healthy = data?.healthy ?? 0;
  const online = data?.online ?? 0;
  const critical = data?.critical ?? 0;
  const score = total > 0 ? (healthy / total) * 100 : 0;

  const r = 55;
  const circumference = 2 * Math.PI * r;
  const offset = circumference - (score / 100) * circumference;
  const color = score > 80 ? "var(--status-online)" : score > 50 ? "var(--status-warning)" : "var(--status-critical)";

  // Apply thresholds if configured
  const thresholds = (config.thresholds as Array<{ value: number; color: string }>) ?? [];
  const thresholdColor = useMemo(() => {
    if (thresholds.length === 0) return undefined;
    const sorted = [...thresholds].sort((a, b) => b.value - a.value);
    return sorted.find((t) => score >= t.value)?.color;
  }, [thresholds, score]);

  const ringColor = thresholdColor ?? color;

  return (
    <div className="h-full flex items-center gap-4 px-2">
      <svg viewBox="0 0 120 120" className="h-full max-h-[120px] w-auto shrink-0">
        <circle cx="60" cy="60" r={r} fill="none" stroke="currentColor" strokeWidth="10" className="text-muted/20" />
        <circle
          cx="60" cy="60" r={r} fill="none"
          stroke={ringColor}
          strokeWidth="10"
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          transform="rotate(-90 60 60)"
          className="transition-all duration-700"
        />
        <text x="60" y="60" textAnchor="middle" dominantBaseline="central"
          className="fill-foreground text-lg font-semibold" fontSize="20">
          {score.toFixed(decimalPrecision)}%
        </text>
      </svg>
      <div className="flex flex-col gap-1 min-w-0">
        <div className="text-sm font-medium">{healthy}/{total} healthy</div>
        <div className="text-xs text-muted-foreground">{online} online, {critical} critical</div>
      </div>
    </div>
  );
}
```

**Note:** The `fetchFleetSummary` and `fetchFleetHealth` API functions should already exist (used by the old renderers). Check the imports and adjust paths if needed.

## Step 2: Update widget registry

**File:** `frontend/src/features/dashboard/widgets/widget-registry.ts`

Replace the three separate fleet widget entries with ONE `fleet_overview` widget:

```typescript
// REMOVE these three entries:
// - device_count
// - fleet_status
// - health_score

// ADD this single entry:
WIDGET_REGISTRY.set("fleet_overview", {
  type: "fleet_overview",
  label: "Fleet Overview",
  description: "Configurable fleet status display. Show device counts, status donut, or health score.",
  category: "fleet",
  icon: "Activity",
  defaultTitle: "Fleet Overview",
  defaultSize: { w: 3, h: 2 },
  minSize: { w: 2, h: 1 },
  maxSize: { w: 6, h: 6 },
  defaultConfig: { display_mode: "count" },
  component: () => import("./renderers/FleetOverviewRenderer"),
});
```

Update the `WidgetType` type to include `"fleet_overview"` and remove the old three types.

**BUT** — keep backward compatibility for existing widgets. Add a migration fallback in `getWidgetDefinition()`:

```typescript
export function getWidgetDefinition(type: string): WidgetDefinition {
  // Backward compatibility: map old fleet types to fleet_overview
  const mappedType =
    type === "device_count" || type === "fleet_status" || type === "health_score"
      ? "fleet_overview"
      : type;

  return WIDGET_REGISTRY.get(mappedType) ?? WIDGET_REGISTRY.get("fleet_overview")!;
}
```

Also map old types to their default display_mode in `getWidgetRenderer()`:

```typescript
// In getWidgetRenderer or WidgetContainer:
if (widgetType === "device_count") config = { ...config, display_mode: "count" };
if (widgetType === "fleet_status") config = { ...config, display_mode: "donut" };
if (widgetType === "health_score") config = { ...config, display_mode: "health" };
```

## Step 3: Add display_mode selector to WidgetConfigDialog

**File:** `frontend/src/features/dashboard/WidgetConfigDialog.tsx`

For `fleet_overview` widgets (and the backward-compat old types), show a display mode selector:

```tsx
{(widgetType === "fleet_overview" || widgetType === "device_count" || widgetType === "fleet_status" || widgetType === "health_score") && (
  <div className="space-y-1">
    <Label htmlFor="display_mode">Display Mode</Label>
    <Select
      value={(localConfig.display_mode as string) ?? "count"}
      onValueChange={(v) => setLocalConfig((c) => ({ ...c, display_mode: v }))}
    >
      <SelectTrigger id="display_mode">
        <SelectValue />
      </SelectTrigger>
      <SelectContent>
        <SelectItem value="count">Device Count</SelectItem>
        <SelectItem value="donut">Status Donut</SelectItem>
        <SelectItem value="health">Health Score</SelectItem>
      </SelectContent>
    </Select>
  </div>
)}
```

## Step 4: Keep old renderer files but mark as deprecated

Do NOT delete `DeviceCountRenderer.tsx`, `FleetStatusRenderer.tsx`, or `HealthScoreRenderer.tsx`. They may be imported elsewhere. Just leave them — the registry no longer references them for new widgets, and the backward-compat mapping handles existing ones.

## Checkpoint

```bash
cd frontend && npx tsc --noEmit
```

After this task: add a "Fleet Overview" widget, verify the display mode dropdown switches between count/donut/health views. Also verify any existing dashboard with old `device_count`/`fleet_status`/`health_score` widgets still renders correctly.
