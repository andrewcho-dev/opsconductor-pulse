# Task 10: Build Verification and Regression Fix

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

## Step 3: Verify Lucide icon availability

If any Lucide icons (AreaChart, ScatterChart, Radar) caused import errors:

```bash
cd frontend && grep -r "export.*AreaChart\b" node_modules/lucide-react/dist/ | head -1
cd frontend && grep -r "export.*ScatterChart\b" node_modules/lucide-react/dist/ | head -1
cd frontend && grep -r "export.*Radar\b" node_modules/lucide-react/dist/ | head -1
```

Replace missing icons with alternatives:
- `AreaChart` → `TrendingUp`
- `ScatterChart` → `Target`
- `Radar` → `Crosshair`

## Step 4: Functional verification checklist

### Gauge styles
- [ ] Add a gauge widget → default "arc" style renders (existing behavior)
- [ ] Open config → select "Speedometer" → pointer appears, semicircle layout
- [ ] Select "Ring" → minimal circular progress, large center text
- [ ] Select "Grade" → 3-color segmented bands with small pointer
- [ ] Add thresholds → colors apply correctly to all 4 styles

### Chart sub-types
- [ ] Line chart → toggle "Smooth Curves" off → angular line segments
- [ ] Toggle "Step Line" on → step interpolation
- [ ] Toggle "Area Fill" on → area fill appears under line
- [ ] Bar chart → toggle "Horizontal" on → bars render horizontally
- [ ] Toggle "Stacked" on → bars stack (single series = no visible change, but no errors)

### Area chart
- [ ] Add "Area Chart" widget → gradient-filled area chart renders
- [ ] Select a device and metric → data appears
- [ ] Toggle "Stacked" → no error
- [ ] Area chart shows in Display As options for line/bar widgets
- [ ] Line chart can switch to Area via Display As dropdown

### Stat card
- [ ] Add "Stat Card" widget → value displays with metric label
- [ ] KPI tile → open config → Display As shows "Stat Card" option
- [ ] Switch KPI to Stat Card → renders as stat card
- [ ] If sparkline_device is set, sparkline background appears

### Pie / Donut
- [ ] Add "Pie / Donut" widget → donut chart of fleet status renders
- [ ] Open config → switch data source to "Alert Severity" → pie updates
- [ ] Toggle "Donut Style" off → full filled pie chart
- [ ] Toggle "Show Labels" off → labels disappear

### Scatter plot
- [ ] Add "Scatter Plot" widget → scatter plot renders (may need device data)
- [ ] Open config → change X/Y metrics → axes update
- [ ] Change time range → data refreshes
- [ ] Thresholds → horizontal line appears at threshold value

### Radar chart
- [ ] Add "Radar Chart" widget → spider chart with 3 default metrics
- [ ] Open config → check additional metrics → axes increase
- [ ] Uncheck to 3 → warning appears if trying to go below 3
- [ ] Max 6 metrics enforced

### Display As switching
- [ ] Line chart: can switch to Area, Bar (3 options)
- [ ] Bar chart: can switch to Line, Area (3 options)
- [ ] Area chart: can switch to Line, Bar (3 options)
- [ ] KPI tile: can switch to Stat Card, Gauge (3 options)
- [ ] Gauge: can switch to KPI, Stat Card (3 options)
- [ ] Stat Card: can switch to KPI, Gauge (3 options)
- [ ] Scatter: no Display As dropdown (standalone)
- [ ] Radar: no Display As dropdown (standalone)
- [ ] Pie: no Display As dropdown (standalone)
- [ ] Table: no Display As dropdown (unchanged)
- [ ] Alert Feed: no Display As dropdown (unchanged)
- [ ] Fleet Overview: uses display_mode (unchanged)

### Widget catalog
- [ ] Open Add Widget drawer → 12 widget types visible
- [ ] Charts category: Line, Area, Bar, Pie/Donut, Scatter, Radar (6)
- [ ] Metrics category: KPI Tile, Stat Card, Gauge (3)
- [ ] Data category: Device Table, Alert Feed (2)
- [ ] Fleet Overview category: Fleet Overview (1)

### Dark mode
- [ ] All new chart types render correctly in dark mode
- [ ] Gauge styles use correct contrast
- [ ] Area chart gradient fades to transparent (not white) in dark mode
- [ ] Radar chart grid lines are visible in dark mode
- [ ] Scatter plot dots are visible against dark background
- [ ] Stat card sparkline uses appropriate opacity

## Step 5: Fix common issues

### React.lazy memoization
If WidgetContainer's `useMemo(() => React.lazy(...))` causes issues with new display_as values not updating the renderer, try clearing by keying on display_as:

```tsx
// In useMemo dependency array, ensure effectiveConfig is included
const LazyComponent = useMemo(() => {
  if (!definition) return null;
  const loader = getWidgetRenderer(widget.widget_type, effectiveConfig);
  return lazy(loader as () => Promise<{ default: ComponentType<WidgetRendererProps> }>);
}, [definition, widget.widget_type, effectiveConfig]);
```

### Missing Lucide icons
If `AreaChart`, `ScatterChart`, or `Radar` don't exist:
```tsx
// Use alternatives that definitely exist in lucide-react
import { TrendingUp as AreaChart } from "lucide-react"; // if AreaChart missing
import { Target as ScatterChart } from "lucide-react";   // if ScatterChart missing
import { Crosshair as Radar } from "lucide-react";       // if Radar missing
```

### useQueries import
If `useQueries` is not available from `@tanstack/react-query`, it was added in v4. Check version:
```bash
cd frontend && grep "@tanstack/react-query" package.json
```
If it's v4+, `useQueries` should be available. If not, replace with individual `useQuery` calls.

## Step 6: Final lint

```bash
cd frontend && npx tsc --noEmit
```

Zero errors before continuing.
