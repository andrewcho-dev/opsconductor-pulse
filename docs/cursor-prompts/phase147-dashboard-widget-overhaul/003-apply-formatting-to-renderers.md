# Task 3: Apply Formatting Config to Renderers

## Context

Task 2 added formatting controls to the config dialog. Now each renderer must read and apply these config values. All formatting fields are optional — use sensible defaults when missing.

## Helper: Extract formatting from config

Each renderer receives `config: Record<string, unknown>`. Extract formatting fields with defaults:

```typescript
const decimalPrecision = (config.decimal_precision as number) ?? 1;
const showLegend = (config.show_legend as boolean) ?? true;
const showXAxis = (config.show_x_axis as boolean) ?? true;
const showYAxis = (config.show_y_axis as boolean) ?? true;
const yAxisMin = config.y_axis_min as number | undefined;
const yAxisMax = config.y_axis_max as number | undefined;
```

## File 1: LineChartRenderer.tsx

**File:** `frontend/src/features/dashboard/widgets/renderers/LineChartRenderer.tsx`

Extract formatting config near the top of the component. Update the ECharts option:

```typescript
const option = useMemo<EChartsOption>(() => {
  // ... existing data processing ...
  return {
    tooltip: { trigger: "axis" },
    legend: showLegend ? {} : { show: false },
    grid: {
      left: showYAxis ? 30 : 10,
      right: 10,
      top: 10,
      bottom: showXAxis ? 30 : 10,
    },
    xAxis: {
      type: "category",
      data: x,
      axisLabel: { hideOverlap: true, show: showXAxis },
      axisTick: { show: showXAxis },
      axisLine: { show: showXAxis },
    },
    yAxis: {
      type: "value",
      scale: true,
      min: yAxisMin,
      max: yAxisMax,
      axisLabel: { show: showYAxis },
      axisTick: { show: showYAxis },
      axisLine: { show: showYAxis },
      splitLine: { show: showYAxis },
    },
    series: [
      {
        type: "line",
        data: y,
        showSymbol: false,
        smooth: true,
      },
    ],
  };
}, [data, showLegend, showXAxis, showYAxis, yAxisMin, yAxisMax]);
```

Add `showLegend`, `showXAxis`, `showYAxis`, `yAxisMin`, `yAxisMax` to the useMemo dependency array.

## File 2: BarChartRenderer.tsx

**File:** `frontend/src/features/dashboard/widgets/renderers/BarChartRenderer.tsx`

Same pattern — extract formatting config and apply to the ECharts option:

```typescript
xAxis: {
  type: "category",
  data: categories,
  axisLabel: { show: showXAxis },
  axisTick: { show: showXAxis },
  axisLine: { show: showXAxis },
},
yAxis: {
  type: "value",
  min: yAxisMin,
  max: yAxisMax,
  axisLabel: { show: showYAxis },
  axisTick: { show: showYAxis },
  axisLine: { show: showYAxis },
  splitLine: { show: showYAxis },
},
```

## File 3: GaugeRenderer.tsx

**File:** `frontend/src/features/dashboard/widgets/renderers/GaugeRenderer.tsx`

Apply `decimalPrecision` to the gauge detail formatter:

```typescript
detail: {
  valueAnimation: true,
  formatter: (v: number) => `${Number(v).toFixed(decimalPrecision)}%`,
  fontSize: 18,
},
```

## File 4: FleetStatusRenderer.tsx

**File:** `frontend/src/features/dashboard/widgets/renderers/FleetStatusRenderer.tsx`

Apply `showLegend`:

```typescript
legend: showLegend ? {
  bottom: 0,
  textStyle: { color: legendColor },
} : { show: false },
```

## File 5: KpiTileRenderer.tsx

**File:** `frontend/src/features/dashboard/widgets/renderers/KpiTileRenderer.tsx`

Apply `decimalPrecision` to the value formatting. Find where the value is displayed (the `text-2xl font-semibold` element) and update:

```typescript
// For percentage values:
const formatted = metric === "uptime_pct"
  ? `${value.toFixed(decimalPrecision)}%`
  : value.toLocaleString(undefined, {
      minimumFractionDigits: 0,
      maximumFractionDigits: decimalPrecision,
    });
```

## File 6: DeviceCountRenderer.tsx

**File:** `frontend/src/features/dashboard/widgets/renderers/DeviceCountRenderer.tsx`

Apply `decimalPrecision` to the total count display:

```typescript
const formatted = total.toLocaleString(undefined, {
  minimumFractionDigits: 0,
  maximumFractionDigits: decimalPrecision,
});
```

## File 7: HealthScoreRenderer.tsx

**File:** `frontend/src/features/dashboard/widgets/renderers/HealthScoreRenderer.tsx`

Apply `decimalPrecision` to the health score percentage display:

```typescript
const formatted = `${score.toFixed(decimalPrecision)}%`;
```

## File 8: Apply show_title in WidgetContainer

**File:** `frontend/src/features/dashboard/widgets/WidgetContainer.tsx`

Read `show_title` from the widget config and conditionally hide the CardHeader:

```tsx
const showTitle = (widget.config as Record<string, unknown>)?.show_title !== false;

return (
  <Card className="h-full flex flex-col overflow-hidden group">
    {showTitle && (
      <CardHeader className="py-1.5 px-2 flex flex-row items-center justify-between">
        {/* ... existing header content ... */}
      </CardHeader>
    )}
    <CardContent className="p-1.5 flex-1 overflow-hidden min-h-0">
      {/* ... existing content ... */}
    </CardContent>
  </Card>
);
```

**Important:** When `showTitle` is false but `isEditing` is true, still show the edit controls (configure/remove buttons) — render them as a minimal overlay bar instead of hiding them:

```tsx
{!showTitle && isEditing && (
  <div className="absolute top-1 right-1 z-10 flex gap-1">
    {/* configure and remove buttons */}
  </div>
)}
```

Add `relative` to the Card className to support absolute positioning of the edit overlay.

## Checkpoint

```bash
cd frontend && npx tsc --noEmit
```
