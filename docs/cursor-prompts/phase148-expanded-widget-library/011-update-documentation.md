# Task 11: Update Documentation

## Context

Phase 148 significantly expanded the widget system. Update docs to reflect new widget types, gauge styles, chart sub-types, and expanded config fields.

## Files to Update

### 1. `docs/development/frontend.md`

Find the **"Dashboard Widget System"** section (added in Phase 147). Update the following sub-sections:

#### Widget Categories — replace the existing list with:

- **Charts** — time-series and comparison visualizations (line chart, area chart, bar chart, pie/donut, scatter plot, radar)
- **Metrics** — single-value displays (KPI tile, stat card with sparkline, gauge with 4 styles)
- **Data** — tabular/list views (device table, alert feed)
- **Fleet Overview** — consolidated fleet status (count, donut, health score)

#### Widget Config Fields — add these to the existing list:

**Display sub-types:**
- `gauge_style`: `"arc" | "speedometer" | "ring" | "grade"` — selects gauge visual style
- `smooth`: boolean — smooth curve interpolation for line/area charts
- `step`: boolean — step-line interpolation (overrides smooth)
- `area_fill`: boolean — area fill under line chart
- `stacked`: boolean — stacked series for bar/area charts
- `horizontal`: boolean — horizontal bar orientation

**Pie chart fields:**
- `pie_data_source`: `"fleet_status" | "alert_severity"` — data source for pie chart
- `doughnut`: boolean — donut vs filled pie style
- `show_labels`: boolean — show percentage labels on slices

**Scatter chart fields:**
- `x_metric`: string — metric for X axis
- `y_metric`: string — metric for Y axis

**Radar chart fields:**
- `radar_metrics`: string[] — 3-6 metrics for radar axes

#### Renderer Rules — add:

- Gauge renderers MUST support `gauge_style` config and render all 4 styles via ECharts gauge options
- Chart renderers that support sub-types (smooth, step, stacked, horizontal) MUST default to existing behavior when config fields are absent
- Stat card renderers MUST show sparkline only when historical data is available
- New visualization types for existing data shapes should use `display_as` switching, not new widget types
- New visualization types with unique data needs (multi-metric, two-axis) should be standalone widget types

#### Prohibited Patterns — add:

- Creating separate widget types for chart sub-types (use config toggles: smooth, step, stacked, horizontal)
- Hardcoding gauge style (use `config.gauge_style` to determine rendering)
- Separate renderers for pie vs donut (use `config.doughnut` toggle)

### 2. YAML frontmatter updates

**`docs/development/frontend.md`:**
- Set `last-verified` to today's date (2026-02-18)
- Add `148` to the `phases` array

**`docs/index.md`:**
- Set `last-verified` to today's date (2026-02-18)
- Add `148` to the `phases` array

## Verify

```bash
grep "last-verified" docs/development/frontend.md
grep "148" docs/development/frontend.md
grep "148" docs/index.md
grep "gauge_style" docs/development/frontend.md
grep "Scatter" docs/development/frontend.md
grep "Radar" docs/development/frontend.md
```
