# Task 2: Chart Sub-type Controls

## Context

LineChartRenderer currently hardcodes `smooth: true` and BarChartRenderer shows only vertical bars. Users need toggles for smooth/step line interpolation, area fill, stacked series, and horizontal bars — all achievable via simple ECharts config changes.

## Step 1: Update LineChartRenderer

**File:** `frontend/src/features/dashboard/widgets/renderers/LineChartRenderer.tsx`

Read 3 new config fields and apply them to the ECharts series:

```tsx
// After the existing config reads (showLegend, showXAxis, etc.), add:
const isSmooth = (config.smooth as boolean | undefined) ?? true;
const isStep = (config.step as boolean | undefined) ?? false;
const areaFill = (config.area_fill as boolean | undefined) ?? false;
```

In the `option` useMemo, update the series object:

```tsx
series: [
  {
    type: "line",
    data: y,
    showSymbol: false,
    smooth: isStep ? false : isSmooth,
    step: isStep ? "middle" : false,
    areaStyle: areaFill ? { opacity: 0.3 } : undefined,
    markLine:
      thresholds.length > 0
        ? {
            silent: true,
            symbol: "none",
            data: thresholds.map((t) => ({
              yAxis: t.value,
              lineStyle: { color: t.color, type: "dashed", width: 1 },
              label: {
                show: !!t.label,
                formatter: t.label || "",
                position: "insideEndTop",
                fontSize: 10,
                color: t.color,
              },
            })),
          }
        : undefined,
  },
],
```

Add `isSmooth`, `isStep`, and `areaFill` to the `useMemo` dependency array.

## Step 2: Update BarChartRenderer

**File:** `frontend/src/features/dashboard/widgets/renderers/BarChartRenderer.tsx`

Read 2 new config fields:

```tsx
// After existing config reads, add:
const isStacked = (config.stacked as boolean | undefined) ?? false;
const isHorizontal = (config.horizontal as boolean | undefined) ?? false;
```

For horizontal bars, swap xAxis and yAxis types. For stacked, add `stack: "total"` to series.

In the `option` useMemo, update to handle both orientations:

```tsx
const option = useMemo<EChartsOption>(() => {
  const online = data?.online ?? data?.ONLINE ?? 0;
  const stale = data?.STALE ?? 0;
  const offline = data?.offline ?? data?.OFFLINE ?? 0;
  const categories = ["Online", "Stale", "Offline"];
  const values = [online, stale, offline];

  const categoryAxis = {
    type: "category" as const,
    data: categories,
    axisLabel: { show: isHorizontal ? showYAxis : showXAxis },
    axisTick: { show: isHorizontal ? showYAxis : showXAxis },
    axisLine: { show: isHorizontal ? showYAxis : showXAxis },
  };

  const valueAxis = {
    type: "value" as const,
    min: yAxisMin,
    max: yAxisMax,
    axisLabel: { show: isHorizontal ? showXAxis : showYAxis },
    axisTick: { show: isHorizontal ? showXAxis : showYAxis },
    axisLine: { show: isHorizontal ? showXAxis : showYAxis },
    splitLine: { show: isHorizontal ? showXAxis : showYAxis },
  };

  return {
    tooltip: { trigger: "axis" },
    legend: showLegend ? {} : { show: false },
    grid: {
      left: isHorizontal ? (showXAxis ? 30 : 10) : (showYAxis ? 30 : 10),
      right: 10,
      top: 10,
      bottom: isHorizontal ? (showYAxis ? 30 : 10) : (showXAxis ? 30 : 10),
    },
    xAxis: isHorizontal ? valueAxis : categoryAxis,
    yAxis: isHorizontal ? categoryAxis : valueAxis,
    series: [
      {
        type: "bar",
        data: values,
        ...(isStacked ? { stack: "total" } : {}),
        markLine:
          thresholds.length > 0
            ? {
                silent: true,
                symbol: "none",
                data: thresholds.map((t) => ({
                  ...(isHorizontal ? { xAxis: t.value } : { yAxis: t.value }),
                  lineStyle: { color: t.color, type: "dashed", width: 1 },
                  label: {
                    show: !!t.label,
                    formatter: t.label || "",
                    position: "insideEndTop",
                    fontSize: 10,
                    color: t.color,
                  },
                })),
              }
            : undefined,
      },
    ],
  };
}, [data, showLegend, showXAxis, showYAxis, thresholds, yAxisMin, yAxisMax, isStacked, isHorizontal]);
```

## Checkpoint

```bash
cd frontend && npx tsc --noEmit
```
