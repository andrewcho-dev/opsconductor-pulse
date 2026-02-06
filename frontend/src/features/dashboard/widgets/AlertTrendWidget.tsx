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
    refetchInterval: 60000,
  });

  const chartData = data?.trend || [];

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
