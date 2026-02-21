# Task 8: Build Verification and Regression Fix

## Step 1: Type check

```bash
cd frontend && npx tsc --noEmit
```

Fix any TypeScript errors.

## Step 2: Production build

```bash
cd frontend && npm run build
```

Fix any build errors.

## Step 3: Functional verification checklist

### Responsive sizing
- [ ] Line chart widget: resize to 2x2 — chart fills container, no overflow
- [ ] Line chart widget: resize to 6x4 — chart fills larger container
- [ ] Bar chart widget: same resize test
- [ ] Gauge widget: same resize test
- [ ] Fleet Overview (donut mode): same resize test
- [ ] Health Score: SVG scales with container

### Formatting controls
- [ ] Open any widget config → "Formatting" section appears
- [ ] Toggle "Show Title" off → title bar hides, edit controls still accessible
- [ ] Set decimal precision to 0 → KPI/gauge values show integers
- [ ] Set decimal precision to 3 → values show 3 decimal places
- [ ] Toggle "Show Legend" off on a line chart → legend disappears
- [ ] Toggle "Show X Axis" off → x-axis labels/ticks hide
- [ ] Toggle "Show Y Axis" off → y-axis labels/ticks hide
- [ ] Set Y Axis Min/Max → chart respects the bounds

### Thresholds
- [ ] Add a threshold (value: 50, color: red) to a line chart → red dashed line appears at y=50
- [ ] Add a threshold to a bar chart → same markLine behavior
- [ ] Add a threshold to a gauge → color zone appears on the gauge ring
- [ ] Add a threshold to a KPI tile → value text changes color when threshold is exceeded
- [ ] Remove all thresholds → widget reverts to default appearance
- [ ] Add threshold with a label → label appears on the chart line

### Visualization type switcher
- [ ] Create a line chart → open config → "Display As" dropdown shows "Line Chart" and "Bar Chart"
- [ ] Switch to "Bar Chart" → widget re-renders as bar chart with same data
- [ ] Create a KPI tile → open config → "Display As" shows "KPI Tile" and "Gauge"
- [ ] Switch to "Gauge" → widget re-renders as gauge
- [ ] Table and Alert Feed widgets do NOT show "Display As" dropdown

### Widget catalog
- [ ] Open Add Widget drawer → widgets are grouped by category
- [ ] Categories shown: Charts, Metrics, Data, Fleet Overview
- [ ] "Fleet Overview" appears instead of device_count/fleet_status/health_score
- [ ] Descriptions are clear and descriptive

### Fleet Overview widget
- [ ] Add Fleet Overview widget → defaults to "Device Count" mode
- [ ] Open config → "Display Mode" dropdown with Count/Donut/Health options
- [ ] Switch to "Status Donut" → donut chart renders
- [ ] Switch to "Health Score" → SVG ring + stats render
- [ ] Backward compat: existing dashboard with old device_count widget still renders

### Dark mode
- [ ] All new UI elements look correct in dark mode
- [ ] Threshold colors render correctly
- [ ] Gauge color zones render correctly
- [ ] Fleet Overview donut colors are theme-aware

## Step 4: Fix common issues

### React.lazy memoization
If `useMemo(() => React.lazy(...))` causes issues (React.lazy should only be called once), try using `useRef` instead:
```tsx
const componentRef = useRef<React.LazyExoticComponent<...> | null>(null);
const key = `${widget.widget_type}-${(widget.config as any).display_as ?? ""}`;
if (!componentRef.current || prevKeyRef.current !== key) {
  componentRef.current = React.lazy(getWidgetRenderer(widget.widget_type, widget.config));
  prevKeyRef.current = key;
}
const Component = componentRef.current;
```

### Missing imports
If components error on `Switch`, `Label`, or other Shadcn components, ensure they exist:
```bash
cd frontend && npx shadcn@latest add switch label
```

### ECharts resize not triggering
If charts don't resize when the widget container changes size, verify the EChartWrapper's ResizeObserver is working. The chart needs `chart.resize()` called on container size change. The existing ResizeObserver should handle this — if not, add it.

## Step 5: Final lint

```bash
cd frontend && npx tsc --noEmit
```

Zero errors before continuing.
