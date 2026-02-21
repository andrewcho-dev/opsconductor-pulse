# Task 9: Update Documentation

## Context

Phase 147 overhauled the dashboard widget system. Document the new capabilities and conventions.

## Files to Update

### 1. `docs/development/frontend.md`

Add a **"Dashboard Widget System"** section after the Mutation Feedback Conventions section. Include:

#### Widget Architecture
- Widgets are defined in `widget-registry.ts` with type, label, description, category, default size, min/max size, default config, and lazy-loaded renderer component
- Widget config is stored as JSON — no schema migrations needed for new config fields
- `getWidgetRenderer()` resolves the correct renderer, respecting `display_as` overrides
- `getWidgetsByCategory()` groups widgets for the catalog UI

#### Widget Categories
- **Charts** — time-series visualizations (line chart, bar chart)
- **Metrics** — single-value displays (KPI tile, gauge)
- **Data** — tabular/list views (device table, alert feed)
- **Fleet Overview** — consolidated fleet status (count, donut, health score)

#### Widget Config Fields
- **Data fields**: `metric`, `time_range`, `devices`, `limit`, `max_items`, etc. (widget-type specific)
- **Display**: `display_as` (overrides visualization type), `display_mode` (fleet widget mode)
- **Formatting**: `decimal_precision`, `show_title`, `show_legend`, `show_x_axis`, `show_y_axis`, `y_axis_min`, `y_axis_max`
- **Thresholds**: `thresholds: [{ value, color, label? }]` — rendered as markLines on charts, color zones on gauges, value coloring on KPIs

#### Renderer Rules
- All ECharts renderers MUST use `style={{ width: "100%", height: "100%" }}` — never fixed pixel heights
- All renderers MUST handle missing config fields gracefully with defaults
- All numeric displays MUST respect `decimal_precision` from config
- Chart renderers MUST apply `show_legend`, `show_x_axis`, `show_y_axis` to their ECharts options
- New renderers MUST be wrapped in `min-h-[100px]` or `min-h-[120px]` to prevent collapse

#### Prohibited Patterns
- Fixed pixel heights on ECharts containers (use percentage-based sizing)
- Hardcoded decimal places (use `config.decimal_precision`)
- Creating new widget types for variations of existing data (use `display_as` or `display_mode`)
- Skipping threshold support in new numeric renderers

Update YAML frontmatter:
- Set `last-verified` to today's date (2026-02-18)
- Add `147` to the `phases` array

### 2. `docs/index.md`

Update YAML frontmatter:
- Set `last-verified` to today's date (2026-02-18)
- Add `147` to the `phases` array

## Verify

```bash
grep "last-verified" docs/development/frontend.md
grep "147" docs/development/frontend.md
grep "147" docs/index.md
```
