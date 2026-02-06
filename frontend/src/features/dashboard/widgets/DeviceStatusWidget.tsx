import { memo, useMemo } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { EChartWrapper } from "@/lib/charts/EChartWrapper";
import { useDevices } from "@/hooks/use-devices";
import { PieChart } from "lucide-react";
import type { EChartsOption } from "echarts";
import { useUIStore } from "@/stores/ui-store";

function DeviceStatusWidgetInner() {
  const { data, isLoading } = useDevices(500, 0);
  const devices = data?.devices || [];
  const resolvedTheme = useUIStore((s) => s.resolvedTheme);
  const isDark = resolvedTheme === "dark";
  const legendColor = isDark ? "#a1a1aa" : "#52525b";
  const borderColor = isDark ? "#18181b" : "#e4e4e7";
  const labelColor = isDark ? "#fafafa" : "#18181b";
  const onlineColor = isDark ? "#22c55e" : "#16a34a";
  const staleColor = isDark ? "#f97316" : "#ea580c";

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
      textStyle: { color: legendColor },
    },
    series: [
      {
        type: "pie",
        radius: ["50%", "70%"],
        center: ["50%", "45%"],
        avoidLabelOverlap: false,
        itemStyle: {
          borderRadius: 4,
          borderColor,
          borderWidth: 2,
        },
        label: {
          show: true,
          position: "center",
          formatter: () => `${devices.length}\nDevices`,
          fontSize: 16,
          fontWeight: "bold",
          color: labelColor,
          lineHeight: 22,
        },
        labelLine: { show: false },
        data: [
          { value: statusCounts.online, name: "Online", itemStyle: { color: onlineColor } },
          { value: statusCounts.stale, name: "Stale", itemStyle: { color: staleColor } },
        ],
      },
    ],
  }), [
    devices.length,
    statusCounts,
    legendColor,
    borderColor,
    labelColor,
    onlineColor,
    staleColor,
  ]);

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
