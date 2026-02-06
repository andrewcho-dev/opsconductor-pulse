import { PageHeader } from "@/components/shared";
import { WidgetErrorBoundary } from "@/components/shared/WidgetErrorBoundary";
import {
  StatCardsWidget,
  AlertStreamWidget,
  DeviceTableWidget,
  FleetHealthWidget,
  AlertTrendWidget,
  DeviceStatusWidget,
} from "./widgets";

export default function DashboardPage() {
  return (
    <div className="space-y-6">
      <PageHeader
        title="Dashboard"
        description="Real-time overview of your IoT fleet"
      />

      {/* Row 1: Stat cards */}
      <WidgetErrorBoundary widgetName="Stat Cards">
        <StatCardsWidget />
      </WidgetErrorBoundary>

      {/* Row 2: Fleet health gauges (full width) */}
      <WidgetErrorBoundary widgetName="Fleet Health">
        <FleetHealthWidget />
      </WidgetErrorBoundary>

      {/* Row 3: Charts - Alert trend + Device status pie */}
      <div className="grid gap-6 lg:grid-cols-3">
        <div className="lg:col-span-2">
          <WidgetErrorBoundary widgetName="Alert Trend">
            <AlertTrendWidget />
          </WidgetErrorBoundary>
        </div>
        <WidgetErrorBoundary widgetName="Device Status">
          <DeviceStatusWidget />
        </WidgetErrorBoundary>
      </div>

      {/* Row 4: Alerts + Devices tables */}
      <div className="grid gap-6 lg:grid-cols-2">
        <WidgetErrorBoundary widgetName="Alert Stream">
          <AlertStreamWidget />
        </WidgetErrorBoundary>

        <WidgetErrorBoundary widgetName="Device Table">
          <DeviceTableWidget />
        </WidgetErrorBoundary>
      </div>
    </div>
  );
}
