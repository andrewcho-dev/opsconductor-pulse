import { PageHeader } from "@/components/shared";
import { WidgetErrorBoundary } from "@/components/shared/WidgetErrorBoundary";
import {
  StatCardsWidget,
  AlertStreamWidget,
  DeviceTableWidget,
} from "./widgets";

export default function DashboardPage() {
  return (
    <div className="space-y-6">
      <PageHeader
        title="Dashboard"
        description="Real-time overview of your IoT fleet"
      />

      <WidgetErrorBoundary widgetName="Stat Cards">
        <StatCardsWidget />
      </WidgetErrorBoundary>

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
