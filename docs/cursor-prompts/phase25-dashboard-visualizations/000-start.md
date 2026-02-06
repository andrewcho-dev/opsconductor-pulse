# Phase 25: Dashboard Visualizations

## Overview

Add visual charts and gauges to the main dashboard. Currently the dashboard only shows stat cards, an alert list, and a device table — no charts.

## Current State

**Dashboard (`/dashboard`) shows:**
- StatCardsWidget (4 number cards)
- AlertStreamWidget (list of alerts)
- DeviceTableWidget (table of devices)

**Chart components exist but are unused on dashboard:**
- `MetricGauge` — ECharts gauge (used only on device detail)
- `TimeSeriesChart` — uPlot time series (used only on device detail)

## What We'll Add

| Widget | Description | Chart Type |
|--------|-------------|------------|
| FleetHealthGauges | Avg battery, avg temp, avg signal | MetricGauge × 3 |
| AlertTrendChart | Alert count over last 24h | TimeSeriesChart |
| DeviceStatusChart | Online vs Stale pie chart | ECharts pie |

## Execute Prompts In Order

1. `001-fleet-health-widget.md` — Create FleetHealthGaugesWidget
2. `002-alert-trend-widget.md` — Create AlertTrendWidget
3. `003-device-status-widget.md` — Create DeviceStatusWidget (pie chart)
4. `004-wire-dashboard.md` — Add widgets to DashboardPage

## Key Files

| File | Role |
|------|------|
| `frontend/src/features/dashboard/DashboardPage.tsx` | Main dashboard layout |
| `frontend/src/features/dashboard/widgets/` | Widget components |
| `frontend/src/lib/charts/MetricGauge.tsx` | Existing gauge component |
| `frontend/src/lib/charts/TimeSeriesChart.tsx` | Existing time series |
| `frontend/src/lib/charts/EChartWrapper.tsx` | ECharts wrapper for pie |

## Start Now

Read and execute `001-fleet-health-widget.md`.
