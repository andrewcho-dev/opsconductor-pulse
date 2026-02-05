import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { MetricGauge } from "@/lib/charts";
import { getLatestValue, getMetricValues } from "@/lib/charts/transforms";
import type { TelemetryPoint } from "@/services/api/types";
import { memo } from "react";

interface MetricGaugesSectionProps {
  metrics: string[];
  points: TelemetryPoint[];
}

function MetricGaugesSectionInner({
  metrics,
  points,
}: MetricGaugesSectionProps) {
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
        <CardTitle className="text-lg">Current Metrics</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="grid gap-2 grid-cols-2 lg:grid-cols-4">
          {metrics.map((metricName) => (
            <MetricGauge
              key={metricName}
              metricName={metricName}
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
