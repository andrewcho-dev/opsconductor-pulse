import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Skeleton } from "@/components/ui/skeleton";
import { Button } from "@/components/ui/button";
import { TimeSeriesChart, TIME_RANGES, type TimeRange } from "@/lib/charts";
import type { TelemetryPoint } from "@/services/api/types";
import { useQueries, useQuery } from "@tanstack/react-query";
import { downloadTelemetryCSV, fetchTelemetryHistory } from "@/services/api/devices";
import { listDeviceSensors } from "@/services/api/sensors";
import { Loader2 } from "lucide-react";
import { memo, useMemo, useState } from "react";

interface TelemetryChartsSectionProps {
  deviceId: string;
  metrics: string[];
  points: TelemetryPoint[];
  isLoading: boolean;
  isLive: boolean;
  liveCount: number;
  timeRange: TimeRange;
  onTimeRangeChange: (range: TimeRange) => void;
}

function TelemetryChartsSectionInner({
  deviceId,
  metrics,
  points,
  isLoading,
  isLive,
  liveCount,
  timeRange,
  onTimeRangeChange,
}: TelemetryChartsSectionProps) {
  const [downloading, setDownloading] = useState(false);
  const [downloadError, setDownloadError] = useState<string | null>(null);
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
  const historyQueries = useQueries({
    queries: metricsToShow.map((metricName) => ({
      queryKey: ["telemetry-history", deviceId, metricName, timeRange],
      queryFn: () => fetchTelemetryHistory(deviceId, metricName, timeRange),
      enabled: !!deviceId,
    })),
  });

  const { data: sensorsData } = useQuery({
    queryKey: ["device-sensors", deviceId],
    queryFn: () => listDeviceSensors(deviceId),
    enabled: !!deviceId,
  });

  const sensorMap = useMemo(() => {
    const map = new Map<string, { label: string; unit: string; type: string }>();
    for (const s of sensorsData?.sensors ?? []) {
      // Backward compatible with both legacy `sensors` shape and Phase 169 `device_sensors` shape.
      const anyS = s as unknown as Record<string, unknown>;
      const metricKey =
        (anyS.metric_key as string | undefined) ?? (anyS.metric_name as string | undefined) ?? "";
      if (!metricKey) continue;
      const label =
        (anyS.display_name as string | undefined) ??
        (anyS.label as string | undefined) ??
        metricKey;
      const unit = (anyS.unit as string | undefined) ?? "";
      const type =
        (anyS.sensor_type as string | undefined) ??
        (((anyS.template_metric as object | null) && "template") as string) ??
        "";
      map.set(metricKey, { label, unit, type });
    }
    return map;
  }, [sensorsData]);
  async function handleDownloadCSV() {
    try {
      setDownloadError(null);
      setDownloading(true);
      await downloadTelemetryCSV(deviceId, timeRange);
    } catch (error) {
      setDownloadError(error instanceof Error ? error.message : "Download failed");
    } finally {
      setDownloading(false);
    }
  }

  return (
    <Card>
      <CardHeader className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between py-2">
        <div className="flex items-center gap-2">
          <CardTitle className="text-sm">Telemetry</CardTitle>
          {isLive && (
            <Badge
              variant="outline"
              className="text-xs text-status-online border-status-online"
            >
              LIVE ({liveCount})
            </Badge>
          )}
        </div>

        <div className="flex items-center gap-2">
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
          <Button
            size="sm"
            variant="outline"
            disabled={downloading}
            onClick={handleDownloadCSV}
          >
            {downloading ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
            Download CSV
          </Button>
        </div>
      </CardHeader>

      <CardContent className="pt-2">
        {downloadError ? (
          <p className="text-sm text-destructive mb-2">{downloadError}</p>
        ) : null}
        {isLoading ? (
          <div className="grid grid-cols-3 gap-2">
            {[1, 2, 3, 4, 5, 6].map((i) => (
              <Skeleton key={i} className="h-32 w-full" />
            ))}
          </div>
        ) : metricsToShow.length === 0 ? (
          <p className="text-sm text-muted-foreground text-center py-4">
            No telemetry data in the selected time range.
          </p>
        ) : (
          <div className="grid grid-cols-3 gap-2">
            {metricsToShow.map((metricName, idx) => (
              <div key={metricName} className="border rounded p-2">
                <div className="text-sm text-muted-foreground mb-1">
                  {sensorMap.get(metricName)?.label ?? metricName}
                  {sensorMap.get(metricName)?.unit
                    ? ` (${sensorMap.get(metricName)?.unit})`
                    : ""}
                </div>
                {historyQueries[idx]?.data?.points?.length ? (
                  <TimeSeriesChart
                    metricName={metricName}
                    displayLabel={sensorMap.get(metricName)?.label ?? metricName}
                    unit={sensorMap.get(metricName)?.unit ?? ""}
                    points={historyQueries[idx].data.points
                      .filter((p) => p.avg !== null)
                      .map((p) => ({
                        timestamp: p.time,
                        metrics: { [metricName]: p.avg as number },
                      }))}
                    colorIndex={idx}
                    height={128}
                  />
                ) : (
                <TimeSeriesChart
                  metricName={metricName}
                  displayLabel={sensorMap.get(metricName)?.label ?? metricName}
                  unit={sensorMap.get(metricName)?.unit ?? ""}
                  points={points}
                  colorIndex={idx}
                  height={128}
                />
                )}
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

export const TelemetryChartsSection = memo(TelemetryChartsSectionInner);
