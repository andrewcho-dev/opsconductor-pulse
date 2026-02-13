import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Skeleton } from "@/components/ui/skeleton";
import { TimeSeriesChart, TIME_RANGES, type TimeRange } from "@/lib/charts";
import type { TelemetryPoint } from "@/services/api/types";
import { memo } from "react";

interface TelemetryChartsSectionProps {
  metrics: string[];
  points: TelemetryPoint[];
  isLoading: boolean;
  isLive: boolean;
  liveCount: number;
  timeRange: TimeRange;
  onTimeRangeChange: (range: TimeRange) => void;
}

function TelemetryChartsSectionInner({
  metrics,
  points,
  isLoading,
  isLive,
  liveCount,
  timeRange,
  onTimeRangeChange,
}: TelemetryChartsSectionProps) {
  const priorityMetrics = [
    "battery_pct",
    "temp_c",
    "rssi_dbm",
    "snr_db",
    "humidity",
    "pressure",
  ];
  const normalized = new Set(metrics);
  const ordered = [
    ...priorityMetrics.filter((m) => normalized.has(m)),
    ...metrics.filter((m) => !priorityMetrics.includes(m)),
  ];
  const metricsToShow = ordered.slice(0, 6);

  return (
    <Card>
      <CardHeader className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between py-2">
        <div className="flex items-center gap-2">
          <CardTitle className="text-xs">Telemetry</CardTitle>
          {isLive && (
            <Badge
              variant="outline"
              className="text-[10px] text-green-700 border-green-200 dark:text-green-400 dark:border-green-700/50"
            >
              LIVE ({liveCount})
            </Badge>
          )}
        </div>

        <Tabs
          value={timeRange}
          onValueChange={(v) => onTimeRangeChange(v as TimeRange)}
        >
          <TabsList>
            {TIME_RANGES.map((tr) => (
              <TabsTrigger key={tr.value} value={tr.value}>
                {tr.label}
              </TabsTrigger>
            ))}
          </TabsList>
        </Tabs>
      </CardHeader>

      <CardContent className="pt-2">
        {isLoading ? (
          <div className="grid grid-cols-3 gap-2">
            {[1, 2, 3, 4, 5, 6].map((i) => (
              <Skeleton key={i} className="h-32 w-full" />
            ))}
          </div>
        ) : metricsToShow.length === 0 ? (
          <p className="text-xs text-muted-foreground text-center py-4">
            No telemetry data in the selected time range.
          </p>
        ) : (
          <div className="grid grid-cols-3 gap-2">
            {metricsToShow.map((metricName, idx) => (
              <div key={metricName} className="border rounded p-2">
                <div className="text-[10px] text-muted-foreground mb-1">
                  {metricName}
                </div>
                <TimeSeriesChart
                  metricName={metricName}
                  points={points}
                  colorIndex={idx}
                  height={128}
                />
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

export const TelemetryChartsSection = memo(TelemetryChartsSectionInner);
