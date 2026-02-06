# Phase 25.4: Wire Widgets to Dashboard

## Task

Add the new visualization widgets to the DashboardPage layout.

## Update DashboardPage

Modify `frontend/src/features/dashboard/DashboardPage.tsx`:

```typescript
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
```

## Layout Summary

```
┌─────────────────────────────────────────────────────┐
│  StatCardsWidget (4 cards)                          │
├─────────────────────────────────────────────────────┤
│  FleetHealthWidget (3 gauges: battery, temp, rssi)  │
├───────────────────────────────────┬─────────────────┤
│  AlertTrendWidget (2/3 width)     │ DeviceStatus    │
│  Line chart: opened/closed        │ Pie chart       │
├───────────────────────────────────┼─────────────────┤
│  AlertStreamWidget                │ DeviceTableWidget│
│  (live alerts list)               │ (device list)   │
└───────────────────────────────────┴─────────────────┘
```

## Verification

```bash
# Build frontend
cd /home/opsconductor/simcloud/frontend && npm run build

# Copy to SPA directory
cp -r dist/* ../services/ui_iot/spa/

# Restart UI service
cd ../compose && docker compose restart ui
```

Then visit the dashboard at `https://<host>/app/` and verify:
- Fleet health gauges show average battery, temp, signal
- Alert trend shows line chart of opened/closed alerts
- Device status shows pie chart of Online vs Stale
- All existing widgets still work

## Files

| Action | File |
|--------|------|
| MODIFY | `frontend/src/features/dashboard/DashboardPage.tsx` |
