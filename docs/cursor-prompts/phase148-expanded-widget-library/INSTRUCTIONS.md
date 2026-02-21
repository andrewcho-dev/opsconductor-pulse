# Phase 148 — Cursor Execution Instructions

Execute these 11 tasks **in order**. Each task depends on the previous one completing successfully. After each task, run `cd frontend && npx tsc --noEmit` to catch errors before moving on.

**Important:** This phase adds new visualization types and expands existing ones. It does NOT change the backend API or database schema (widget config is already JSON). All new renderers use existing API endpoints (fetchTelemetryHistory, fetchFleetSummary, runAnalyticsQuery, etc.).

---

## Task 1: Gauge style expansion

Open and read `docs/cursor-prompts/phase148-expanded-widget-library/001-gauge-styles.md` for full details.

Modify GaugeRenderer to support 4 gauge styles via `gauge_style` config: "arc" (current default), "speedometer" (with pointer), "ring" (minimal progress ring), "grade" (segmented color bands).

**Checkpoint:** `cd frontend && npx tsc --noEmit`

---

## Task 2: Chart sub-type controls

Open and read `docs/cursor-prompts/phase148-expanded-widget-library/002-chart-sub-types.md` for full details.

Add configurable toggles to LineChartRenderer (smooth, step, area_fill) and BarChartRenderer (stacked, horizontal). These are config-driven with no new renderer files.

**Checkpoint:** `cd frontend && npx tsc --noEmit`

---

## Task 3: Area chart renderer

Open and read `docs/cursor-prompts/phase148-expanded-widget-library/003-area-chart-renderer.md` for full details.

Create AreaChartRenderer.tsx — a dedicated area chart with gradient fill, stacked support, and all formatting controls. Uses fetchTelemetryHistory.

**Checkpoint:** `cd frontend && npx tsc --noEmit`

---

## Task 4: Stat card renderer

Open and read `docs/cursor-prompts/phase148-expanded-widget-library/004-stat-card-renderer.md` for full details.

Create StatCardRenderer.tsx — enhanced KPI tile with inline sparkline trend line and trend direction arrow. Fetches recent history for mini chart.

**Checkpoint:** `cd frontend && npx tsc --noEmit`

---

## Task 5: Pie/donut chart renderer

Open and read `docs/cursor-prompts/phase148-expanded-widget-library/005-pie-chart-renderer.md` for full details.

Create PieChartRenderer.tsx — standalone pie/donut chart that can display fleet status distribution, alert severity breakdown, or metric group-by data.

**Checkpoint:** `cd frontend && npx tsc --noEmit`

---

## Task 6: Scatter plot renderer

Open and read `docs/cursor-prompts/phase148-expanded-widget-library/006-scatter-renderer.md` for full details.

Create ScatterRenderer.tsx — two-metric correlation scatter plot using analytics API. Each dot represents a device, axes represent different metrics.

**Checkpoint:** `cd frontend && npx tsc --noEmit`

---

## Task 7: Radar chart renderer

Open and read `docs/cursor-prompts/phase148-expanded-widget-library/007-radar-renderer.md` for full details.

Create RadarRenderer.tsx — spider/radar chart for multi-metric comparison. User selects 3-6 metrics, each becomes a radial axis.

**Checkpoint:** `cd frontend && npx tsc --noEmit`

---

## Task 8: Wire up registry and display options

Open and read `docs/cursor-prompts/phase148-expanded-widget-library/008-wire-registry.md` for full details.

Add all 5 new widget types to WIDGET_REGISTRY, expand DISPLAY_OPTIONS from 4 entries to 12+, add new DISPLAY_RENDERERS, update WidgetType union, update AddWidgetDrawer icons.

**Checkpoint:** `cd frontend && npx tsc --noEmit`

---

## Task 9: Expand config dialog

Open and read `docs/cursor-prompts/phase148-expanded-widget-library/009-wire-config-dialog.md` for full details.

Add gauge style picker, chart sub-type toggles (smooth, step, area fill, stacked, horizontal), pie chart source selector, scatter axis selectors, radar metric multi-selector to WidgetConfigDialog.

**Checkpoint:** `cd frontend && npx tsc --noEmit`

---

## Task 10: Build verification

Open and read `docs/cursor-prompts/phase148-expanded-widget-library/010-verify-and-fix.md` for the complete checklist.

1. `cd frontend && npx tsc --noEmit` — must be zero errors
2. `cd frontend && npm run build` — must succeed
3. Functional checks for all new widget types and configurations

---

## Task 11: Update documentation

Open and read `docs/cursor-prompts/phase148-expanded-widget-library/011-update-documentation.md` for full details.

Update the "Dashboard Widget System" section in `docs/development/frontend.md` with new widget types, gauge styles, chart sub-types, and expanded config fields.
