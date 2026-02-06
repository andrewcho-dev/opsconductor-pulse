import { memo, useMemo } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { MetricGauge } from "@/lib/charts/MetricGauge";
import { useDevices } from "@/hooks/use-devices";
import { Activity } from "lucide-react";

function FleetHealthWidgetInner() {
  const { data, isLoading } = useDevices(500, 0);
  const devices = data?.devices || [];

  // Calculate fleet averages from device state
  const averages = useMemo(() => {
    if (devices.length === 0) return null;

    let batterySum = 0, batteryCount = 0;
    let tempSum = 0, tempCount = 0;
    let rssiSum = 0, rssiCount = 0;

    for (const device of devices) {
      const state = device.state || {};
      if (typeof state.battery_pct === "number") {
        batterySum += state.battery_pct;
        batteryCount++;
      }
      if (typeof state.temp_c === "number") {
        tempSum += state.temp_c;
        tempCount++;
      }
      if (typeof state.rssi_dbm === "number") {
        rssiSum += state.rssi_dbm;
        rssiCount++;
      }
    }

    return {
      battery: batteryCount > 0 ? batterySum / batteryCount : null,
      temp: tempCount > 0 ? tempSum / tempCount : null,
      rssi: rssiCount > 0 ? rssiSum / rssiCount : null,
    };
  }, [devices]);

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <Activity className="h-4 w-4" />
            Fleet Health
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-3 gap-4">
            <Skeleton className="h-[180px]" />
            <Skeleton className="h-[180px]" />
            <Skeleton className="h-[180px]" />
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-base">
          <Activity className="h-4 w-4" />
          Fleet Health
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-3 gap-4">
          <MetricGauge
            metricName="battery_pct"
            value={averages?.battery ?? null}
          />
          <MetricGauge
            metricName="temp_c"
            value={averages?.temp ?? null}
          />
          <MetricGauge
            metricName="rssi_dbm"
            value={averages?.rssi ?? null}
          />
        </div>
      </CardContent>
    </Card>
  );
}

export const FleetHealthWidget = memo(FleetHealthWidgetInner);
