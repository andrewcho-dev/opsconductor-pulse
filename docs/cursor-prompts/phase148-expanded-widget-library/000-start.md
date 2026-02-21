# Phase 148 — Expanded Widget Visualization Library

## Goal

Transform the dashboard from a basic 4-widget system into a competitive IoT visualization platform with 12+ widget types, 4 gauge styles, chart sub-type controls, and industry-standard stat cards with sparklines.

## What changes

### New renderer files (5 new)
- `AreaChartRenderer.tsx` — filled area chart with stacked option
- `StatCardRenderer.tsx` — KPI with inline sparkline trend + trend arrow
- `PieChartRenderer.tsx` — standalone pie/donut chart for any distribution
- `ScatterRenderer.tsx` — two-metric correlation scatter plot
- `RadarRenderer.tsx` — multi-metric spider/radar chart

### Modified renderer files (3 existing)
- `GaugeRenderer.tsx` — 4 gauge styles via `gauge_style` config
- `LineChartRenderer.tsx` — smooth/step/area-fill toggles
- `BarChartRenderer.tsx` — stacked/horizontal toggles

### Modified system files (4 existing)
- `widget-registry.ts` — 5 new widget types, expanded DISPLAY_OPTIONS (12+ options), new DISPLAY_RENDERERS
- `WidgetConfigDialog.tsx` — gauge style picker, chart sub-type toggles, new widget configs
- `AddWidgetDrawer.tsx` — new icon imports
- `dashboards.ts` — WidgetType union expanded

### No backend changes
Widget config is JSON — no schema migrations needed.

## Before / After

| Capability | Phase 147 | Phase 148 |
|-----------|-----------|-----------|
| Chart types | Line, Bar | Line, Bar, Area, Scatter, Radar, Pie/Donut |
| Metric displays | KPI, Gauge (1 style) | KPI, Gauge (4 styles), Stat Card w/ sparkline |
| Display switching | 2 pairs (line↔bar, kpi↔gauge) | 12+ options across all compatible widgets |
| Chart toggles | None | Smooth, Step, Area fill, Stacked, Horizontal |
| Widget catalog | 7 entries | 12 entries |

## Execution order

See `INSTRUCTIONS.md` for the task sequence.
