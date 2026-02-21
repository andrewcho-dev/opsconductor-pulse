# Phase 147 — Dashboard Widget Overhaul

## Problem

The dashboard widget system is a layout engine with 9 hardcoded renderers. Users cannot:
- Switch visualization type for the same data
- Configure thresholds, colors, or axis formatting
- Control decimal precision, legend visibility, or title visibility
- Resize widgets without charts clipping (fixed pixel heights)

Every major IoT platform (AWS SiteWise, Azure IoT Central, ThingsBoard, Ubidots, Datacake) provides these capabilities as table-stakes features.

## Goals

1. Charts fill their container dynamically — no fixed pixel heights
2. Users can switch visualization type (line → bar → gauge → KPI) for compatible widgets
3. Threshold configuration with color zones (red/yellow/green at configurable values)
4. Formatting controls: decimal precision, axis visibility, legend toggle, Y-axis bounds, title toggle
5. Improved widget catalog with categories and better descriptions
6. Consolidate 3 redundant fleet widgets into 1 configurable widget

## Architecture

- **EChartWrapper** already has ResizeObserver — renderers just need to stop overriding with fixed heights
- **Widget config** is JSON in the database — no schema migration needed, just handle new fields on frontend
- **`display_as`** config field overrides the default renderer for a widget type
- **Thresholds** stored in config as `thresholds: [{ value, color, label? }]`, rendered via ECharts `markLine` on charts and color logic on KPIs/gauges
- **Formatting** stored in config as `show_legend`, `show_x_axis`, `show_y_axis`, `y_axis_min`, `y_axis_max`, `decimal_precision`, `show_title`

## Execution Order

| Task | File(s) | Description |
|------|---------|-------------|
| 001 | EChartWrapper, all renderers, WidgetContainer | Responsive chart sizing |
| 002 | WidgetConfigDialog, widget-registry | Add formatting controls to config dialog |
| 003 | All renderers | Apply formatting config to renderers |
| 004 | WidgetConfigDialog, chart renderers, KPI, gauge | Threshold configuration + rendering |
| 005 | widget-registry, WidgetContainer, WidgetConfigDialog | Visualization type switcher |
| 006 | widget-registry, AddWidgetDrawer | Improve widget catalog |
| 007 | widget-registry, renderers | Consolidate fleet widgets |
| 008 | All | Verification |
| 009 | docs | Documentation |

## Rules

- Keep all existing widget types working — no breaking changes
- Config fields are optional — renderers must handle missing config gracefully with defaults
- Use ECharts built-in features (markLine, axisLabel, legend) — don't build custom rendering
- Run `cd frontend && npx tsc --noEmit` after every task
