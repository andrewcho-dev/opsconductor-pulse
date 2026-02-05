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
  return (
    <Card>
      <CardHeader className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-center gap-2">
          <CardTitle className="text-lg">Telemetry History</CardTitle>
          {isLive && (
            <Badge
              variant="outline"
              className="text-[10px] text-green-400 border-green-700/50"
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

      <CardContent className="space-y-6">
        {isLoading ? (
          <div className="space-y-4">
            {[1, 2, 3].map((i) => (
              <Skeleton key={i} className="h-[200px] w-full" />
            ))}
          </div>
        ) : metrics.length === 0 ? (
          <p className="text-sm text-muted-foreground text-center py-8">
            No telemetry data in the selected time range.
          </p>
        ) : (
          metrics.map((metricName, idx) => (
            <div key={metricName}>
              <TimeSeriesChart
                metricName={metricName}
                points={points}
                colorIndex={idx}
                height={200}
              />
            </div>
          ))
        )}
      </CardContent>
    </Card>
  );
}

export const TelemetryChartsSection = memo(TelemetryChartsSectionInner);
