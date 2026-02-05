import { useParams, Link } from "react-router-dom";
import { useDevice } from "@/hooks/use-devices";
import { useDeviceTelemetry } from "@/hooks/use-device-telemetry";
import { WidgetErrorBoundary } from "@/components/shared/WidgetErrorBoundary";
import { DeviceInfoCard } from "./DeviceInfoCard";
import { MetricGaugesSection } from "./MetricGaugesSection";
import { TelemetryChartsSection } from "./TelemetryChartsSection";
import { DeviceAlertsSection } from "./DeviceAlertsSection";
import { ArrowLeft } from "lucide-react";

export default function DeviceDetailPage() {
  const { deviceId } = useParams<{ deviceId: string }>();

  // Device info from REST
  const { data: deviceData, isLoading: deviceLoading } = useDevice(deviceId || "");

  // Telemetry data (REST + WS fused)
  const {
    points,
    metrics,
    isLoading: telemetryLoading,
    isLive,
    liveCount,
    timeRange,
    setTimeRange,
  } = useDeviceTelemetry(deviceId || "");

  return (
    <div className="space-y-6">
      {/* Back navigation */}
      <Link
        to="/devices"
        className="inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground transition-colors"
      >
        <ArrowLeft className="h-4 w-4" />
        Back to Devices
      </Link>

      {/* Device Info */}
      <WidgetErrorBoundary widgetName="Device Info">
        <DeviceInfoCard
          device={deviceData?.device}
          isLoading={deviceLoading}
        />
      </WidgetErrorBoundary>

      {/* Current Metric Gauges */}
      <WidgetErrorBoundary widgetName="Metric Gauges">
        <MetricGaugesSection
          metrics={metrics}
          points={points}
        />
      </WidgetErrorBoundary>

      {/* Telemetry Time-Series Charts */}
      <WidgetErrorBoundary widgetName="Telemetry Charts">
        <TelemetryChartsSection
          metrics={metrics}
          points={points}
          isLoading={telemetryLoading}
          isLive={isLive}
          liveCount={liveCount}
          timeRange={timeRange}
          onTimeRangeChange={setTimeRange}
        />
      </WidgetErrorBoundary>

      {/* Device Alerts */}
      {deviceId && (
        <WidgetErrorBoundary widgetName="Device Alerts">
          <DeviceAlertsSection deviceId={deviceId} />
        </WidgetErrorBoundary>
      )}
    </div>
  );
}
