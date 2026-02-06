# Phase 25.3: Device Status Pie Chart Widget

## Task

Create a donut/pie chart showing device status distribution (Online vs Stale).

## Create Widget

Create `frontend/src/features/dashboard/widgets/DeviceStatusWidget.tsx`:

```typescript
import { memo, useMemo } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { EChartWrapper } from "@/lib/charts/EChartWrapper";
import { useDevices } from "@/hooks/use-devices";
import { PieChart } from "lucide-react";
import type { EChartsOption } from "echarts";

function DeviceStatusWidgetInner() {
  const { data, isLoading } = useDevices(500, 0);
  const devices = data?.devices || [];

  const statusCounts = useMemo(() => {
    let online = 0;
    let stale = 0;
    for (const d of devices) {
      if (d.status === "ONLINE") online++;
      else if (d.status === "STALE") stale++;
    }
    return { online, stale };
  }, [devices]);

  const option = useMemo<EChartsOption>(() => ({
    tooltip: {
      trigger: "item",
      formatter: "{b}: {c} ({d}%)",
    },
    legend: {
      bottom: 0,
      textStyle: { color: "#a1a1aa" },
    },
    series: [
      {
        type: "pie",
        radius: ["50%", "70%"],
        center: ["50%", "45%"],
        avoidLabelOverlap: false,
        itemStyle: {
          borderRadius: 4,
          borderColor: "#18181b",
          borderWidth: 2,
        },
        label: {
          show: true,
          position: "center",
          formatter: () => `${devices.length}\nDevices`,
          fontSize: 16,
          fontWeight: "bold",
          color: "#fafafa",
          lineHeight: 22,
        },
        labelLine: { show: false },
        data: [
          { value: statusCounts.online, name: "Online", itemStyle: { color: "#22c55e" } },
          { value: statusCounts.stale, name: "Stale", itemStyle: { color: "#f97316" } },
        ],
      },
    ],
  }), [devices.length, statusCounts]);

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <PieChart className="h-4 w-4" />
            Device Status
          </CardTitle>
        </CardHeader>
        <CardContent>
          <Skeleton className="h-[220px]" />
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-base">
          <PieChart className="h-4 w-4" />
          Device Status
        </CardTitle>
      </CardHeader>
      <CardContent>
        {devices.length === 0 ? (
          <div className="h-[220px] flex items-center justify-center text-muted-foreground">
            No devices
          </div>
        ) : (
          <EChartWrapper option={option} style={{ height: 220 }} />
        )}
      </CardContent>
    </Card>
  );
}

export const DeviceStatusWidget = memo(DeviceStatusWidgetInner);
```

## Update Widget Index

Add to `frontend/src/features/dashboard/widgets/index.ts`:

```typescript
export { DeviceStatusWidget } from "./DeviceStatusWidget";
```

## Verification

```bash
cd /home/opsconductor/simcloud/frontend && npm run build
```

## Files

| Action | File |
|--------|------|
| CREATE | `frontend/src/features/dashboard/widgets/DeviceStatusWidget.tsx` |
| MODIFY | `frontend/src/features/dashboard/widgets/index.ts` |
