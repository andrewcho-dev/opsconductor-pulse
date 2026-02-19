import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { MetricGauge } from "@/lib/charts";
import { getLatestValue, getMetricValues } from "@/lib/charts/transforms";
import type { TelemetryPoint } from "@/services/api/types";
import { useQuery } from "@tanstack/react-query";
import { memo, useMemo } from "react";
import { listDeviceSensors } from "@/services/api/sensors";

interface MetricGaugesSectionProps {
  deviceId?: string;
  metrics: string[];
  points: TelemetryPoint[];
}

function MetricGaugesSectionInner({
  deviceId,
  metrics,
  points,
}: MetricGaugesSectionProps) {
  const { data: sensorsData } = useQuery({
    queryKey: ["device-sensors", deviceId],
    queryFn: () => listDeviceSensors(deviceId!),
    enabled: !!deviceId,
  });

  const sensorMap = useMemo(() => {
    const map = new Map<string, { label: string; unit: string }>();
    for (const s of sensorsData?.sensors ?? []) {
      const key = s.metric_name ?? s.metric_key;
      if (!key) continue;
      map.set(key, { label: s.label || s.metric_name || s.display_name || key, unit: s.unit || "" });
    }
    return map;
  }, [sensorsData]);

  if (metrics.length === 0) {
    return (
      <Card>
        <CardContent className="p-6">
          <p className="text-sm text-muted-foreground text-center py-4">
            No metric data available.
          </p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Current Metrics</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="grid gap-2 grid-cols-2 lg:grid-cols-4">
          {metrics.map((metricName) => (
            <MetricGauge
              key={metricName}
              metricName={metricName}
              displayLabel={sensorMap.get(metricName)?.label}
              unit={sensorMap.get(metricName)?.unit}
              value={getLatestValue(points, metricName)}
              allValues={getMetricValues(points, metricName)}
            />
          ))}
        </div>
      </CardContent>
    </Card>
  );
}

export const MetricGaugesSection = memo(MetricGaugesSectionInner);
