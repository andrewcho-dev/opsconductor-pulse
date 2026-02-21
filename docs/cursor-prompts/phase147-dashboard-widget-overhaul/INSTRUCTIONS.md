# Phase 147 — Cursor Execution Instructions

Execute these 9 tasks **in order**. Each task depends on the previous one completing successfully. After each task, run `cd frontend && npx tsc --noEmit` to catch errors before moving on.

**Important:** This phase overhauls the dashboard widget system. It changes how widgets render and what users can configure, but does NOT change the backend API or database schema (widget config is already JSON).

---

## Task 1: Responsive chart sizing

Open and read `docs/cursor-prompts/phase147-dashboard-widget-overhaul/001-responsive-charts.md` for full details.

Remove fixed pixel heights from all ECharts renderers. Charts must fill their container dynamically using `width: "100%", height: "100%"` with `min-h-[120px]` safety. Update WidgetContainer's CardContent to `overflow-hidden min-h-0`.

**Checkpoint:** `cd frontend && npx tsc --noEmit`

---

## Task 2: Add formatting controls to config dialog

Open and read `docs/cursor-prompts/phase147-dashboard-widget-overhaul/002-formatting-controls.md` for full details.

Add a "Formatting" section to WidgetConfigDialog with: decimal precision, show title toggle, show legend toggle, show X/Y axis toggles, Y axis min/max bounds. Define `WidgetFormatConfig` interface in widget-registry.ts.

**Checkpoint:** `cd frontend && npx tsc --noEmit`

---

## Task 3: Apply formatting to renderers

Open and read `docs/cursor-prompts/phase147-dashboard-widget-overhaul/003-apply-formatting-to-renderers.md` for full details.

Update all 7 renderers + WidgetContainer to read and apply formatting config fields. Charts respect axis/legend toggles. KPIs/gauges respect decimal precision. WidgetContainer hides title when show_title is false.

**Checkpoint:** `cd frontend && npx tsc --noEmit`

---

## Task 4: Threshold configuration + rendering

Open and read `docs/cursor-prompts/phase147-dashboard-widget-overhaul/004-threshold-configuration.md` for full details.

Add threshold config UI (value + color picker + label) to WidgetConfigDialog. Render thresholds as ECharts markLines on line/bar charts, color zones on gauges, and value coloring on KPI tiles.

**Checkpoint:** `cd frontend && npx tsc --noEmit`

---

## Task 5: Visualization type switcher

Open and read `docs/cursor-prompts/phase147-dashboard-widget-overhaul/005-visualization-type-switcher.md` for full details.

Add `display_as` config field that overrides the widget's default renderer. Line↔Bar and KPI↔Gauge switching. Add "Display As" dropdown to config dialog. Update WidgetContainer to resolve renderers via `getWidgetRenderer()`.

**Checkpoint:** `cd frontend && npx tsc --noEmit`

---

## Task 6: Improve widget catalog

Open and read `docs/cursor-prompts/phase147-dashboard-widget-overhaul/006-improve-widget-catalog.md` for full details.

Add `category` field to WidgetDefinition. Group widgets in AddWidgetDrawer by category (Charts, Metrics, Data, Fleet Overview). Improve descriptions.

**Checkpoint:** `cd frontend && npx tsc --noEmit`

---

## Task 7: Consolidate fleet widgets

Open and read `docs/cursor-prompts/phase147-dashboard-widget-overhaul/007-consolidate-fleet-widgets.md` for full details.

Create FleetOverviewRenderer with 3 display modes (count, donut, health). Replace device_count/fleet_status/health_score with single `fleet_overview` widget type. Keep backward compatibility for existing widgets.

**Checkpoint:** `cd frontend && npx tsc --noEmit`

---

## Task 8: Build verification

Open and read `docs/cursor-prompts/phase147-dashboard-widget-overhaul/008-verify-and-fix.md` for the complete checklist.

1. `cd frontend && npx tsc --noEmit` — must be zero errors
2. `cd frontend && npm run build` — must succeed
3. Functional checks for: responsive sizing, formatting controls, thresholds, viz switcher, widget catalog, fleet overview, dark mode

---

## Task 9: Update documentation

Open and read `docs/cursor-prompts/phase147-dashboard-widget-overhaul/009-update-documentation.md` for full details.

Add **"Dashboard Widget System"** section to `docs/development/frontend.md` covering widget architecture, categories, config fields, renderer rules, and prohibited patterns.
