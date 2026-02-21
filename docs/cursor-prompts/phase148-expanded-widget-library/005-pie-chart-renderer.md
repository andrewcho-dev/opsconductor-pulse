# Task 5: Pie/Donut Chart Renderer

## Context

Pie and donut charts are fundamental for showing proportional data — fleet status distribution, alert severity breakdown, device type split. The FleetOverviewRenderer already has a donut view, but it's locked to fleet status data. This is a standalone, configurable pie/donut widget that works with multiple data sources.

## Step 1: Create PieChartRenderer.tsx

**File:** `frontend/src/features/dashboard/widgets/renderers/PieChartRenderer.tsx` (NEW)

```tsx
import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import type { EChartsOption } from "echarts";
import { Skeleton } from "@/components/ui/skeleton";
import { EChartWrapper } from "@/lib/charts/EChartWrapper";
import { fetchFleetSummary } from "@/services/api/devices";
import { fetchAlerts } from "@/services/api/alerts";
import { CHART_COLORS } from "@/lib/charts/colors";
import { useUIStore } from "@/stores/ui-store";
import type { WidgetRendererProps } from "../widget-registry";

type PieDataSource = "fleet_status" | "alert_severity";

export default function PieChartRenderer({ config }: WidgetRendererProps) {
  const dataSource = (config.pie_data_source as PieDataSource) ?? "fleet_status";
  const isDoughnut = (config.doughnut as boolean | undefined) ?? true;
  const showLabels = (config.show_labels as boolean | undefined) ?? true;
  const showLegend = (config.show_legend as boolean | undefined) ?? true;
  const isDark = useUIStore((s) => s.resolvedTheme === "dark");

  // Fleet status data
  const { data: fleetData, isLoading: fleetLoading } = useQuery({
    queryKey: ["widget-pie", "fleet-summary"],
    queryFn: fetchFleetSummary,
    enabled: dataSource === "fleet_status",
    refetchInterval: 30000,
  });

  // Alert severity data
  const { data: alertData, isLoading: alertLoading } = useQuery({
    queryKey: ["widget-pie", "alerts-all"],
    queryFn: () => fetchAlerts("OPEN", 100, 0),
    enabled: dataSource === "alert_severity",
    refetchInterval: 30000,
  });

  const isLoading = fleetLoading || alertLoading;

  const pieData = useMemo(() => {
    if (dataSource === "fleet_status") {
      const online = fleetData?.online ?? fleetData?.ONLINE ?? 0;
      const stale = fleetData?.STALE ?? 0;
      const offline = fleetData?.offline ?? fleetData?.OFFLINE ?? 0;
      return [
        { value: online, name: "Online", itemStyle: { color: "#22c55e" } },
        { value: stale, name: "Stale", itemStyle: { color: "#f59e0b" } },
        { value: offline, name: "Offline", itemStyle: { color: "#ef4444" } },
      ].filter((d) => d.value > 0);
    }

    if (dataSource === "alert_severity") {
      const alerts = alertData?.alerts ?? [];
      const counts: Record<string, number> = {};
      alerts.forEach((a: { severity?: string }) => {
        const sev = a.severity ?? "info";
        counts[sev] = (counts[sev] ?? 0) + 1;
      });
      const severityColors: Record<string, string> = {
        critical: "#ef4444",
        high: "#f97316",
        medium: "#f59e0b",
        low: "#3b82f6",
        info: "#6b7280",
      };
      return Object.entries(counts).map(([name, value], i) => ({
        value,
        name: name.charAt(0).toUpperCase() + name.slice(1),
        itemStyle: { color: severityColors[name] ?? CHART_COLORS[i % CHART_COLORS.length] },
      }));
    }

    return [];
  }, [dataSource, fleetData, alertData]);

  const total = pieData.reduce((sum, d) => sum + d.value, 0);

  const option = useMemo<EChartsOption>(() => ({
    tooltip: { trigger: "item", formatter: "{b}: {c} ({d}%)" },
    legend: showLegend
      ? {
          bottom: 0,
          textStyle: { color: isDark ? "#a1a1aa" : "#52525b", fontSize: 11 },
        }
      : { show: false },
    series: [
      {
        type: "pie",
        radius: isDoughnut ? ["45%", "72%"] : ["0%", "72%"],
        center: ["50%", showLegend ? "45%" : "50%"],
        avoidLabelOverlap: true,
        itemStyle: {
          borderRadius: isDoughnut ? 4 : 0,
          borderColor: isDark ? "#18181b" : "#ffffff",
          borderWidth: 2,
        },
        label: isDoughnut
          ? {
              show: true,
              position: "center",
              formatter: () => `${total}\nTotal`,
              fontSize: 16,
              fontWeight: "bold" as const,
              color: isDark ? "#fafafa" : "#18181b",
              lineHeight: 22,
            }
          : {
              show: showLabels,
              formatter: "{b}: {d}%",
              fontSize: 11,
            },
        labelLine: { show: !isDoughnut && showLabels },
        data: pieData,
      },
    ],
  }), [isDark, isDoughnut, pieData, showLabels, showLegend, total]);

  if (isLoading) return <Skeleton className="h-full w-full min-h-[120px]" />;

  if (pieData.length === 0) {
    return (
      <div className="text-sm text-muted-foreground flex items-center justify-center h-full min-h-[120px]">
        No data available
      </div>
    );
  }

  return (
    <div className="h-full w-full min-h-[120px]">
      <EChartWrapper option={option} style={{ width: "100%", height: "100%" }} />
    </div>
  );
}
```

## Config fields

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `pie_data_source` | `"fleet_status" \| "alert_severity"` | `"fleet_status"` | What data to visualize |
| `doughnut` | `boolean` | `true` | Donut style with center total, or filled pie |
| `show_labels` | `boolean` | `true` | Show percentage labels on slices |
| `show_legend` | `boolean` | `true` | Show legend at bottom |

## Checkpoint

```bash
cd frontend && npx tsc --noEmit
```
