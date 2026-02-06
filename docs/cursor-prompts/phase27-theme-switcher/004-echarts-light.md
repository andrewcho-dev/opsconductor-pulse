# Phase 27.4: Add Light Theme for ECharts

## Task

Add a light theme for ECharts and make charts respond to theme changes.

## Modify theme.ts

**File:** `frontend/src/lib/charts/theme.ts`

```typescript
import * as echarts from "echarts";

export const ECHARTS_DARK_THEME = "pulse-dark";
export const ECHARTS_LIGHT_THEME = "pulse-light";

export function registerPulseThemes() {
  // Dark theme
  echarts.registerTheme(ECHARTS_DARK_THEME, {
    textStyle: { color: "#a1a1aa" },
    backgroundColor: "transparent",
    title: { textStyle: { color: "#fafafa" } },
    legend: { textStyle: { color: "#a1a1aa" } },
    tooltip: {
      backgroundColor: "#18181b",
      borderColor: "#27272a",
      textStyle: { color: "#fafafa" },
    },
    axisLine: { lineStyle: { color: "#3f3f46" } },
    splitLine: { lineStyle: { color: "#27272a" } },
    axisLabel: { color: "#71717a" },
  });

  // Light theme
  echarts.registerTheme(ECHARTS_LIGHT_THEME, {
    textStyle: { color: "#52525b" },
    backgroundColor: "transparent",
    title: { textStyle: { color: "#18181b" } },
    legend: { textStyle: { color: "#52525b" } },
    tooltip: {
      backgroundColor: "#ffffff",
      borderColor: "#e4e4e7",
      textStyle: { color: "#18181b" },
    },
    axisLine: { lineStyle: { color: "#d4d4d8" } },
    splitLine: { lineStyle: { color: "#e4e4e7" } },
    axisLabel: { color: "#71717a" },
  });
}

// For backwards compatibility
export function registerPulseDarkTheme() {
  registerPulseThemes();
}
```

## Modify EChartWrapper.tsx

**File:** `frontend/src/lib/charts/EChartWrapper.tsx`

Make the wrapper respond to theme changes:

```typescript
import { useRef, useEffect, useMemo, memo } from "react";
import * as echarts from "echarts";
import type { EChartsOption, ECharts } from "echarts";
import { useUIStore } from "@/stores/ui-store";
import { ECHARTS_DARK_THEME, ECHARTS_LIGHT_THEME } from "./theme";

interface EChartWrapperProps {
  option: EChartsOption;
  className?: string;
  style?: React.CSSProperties;
}

function EChartWrapperInner({ option, className, style }: EChartWrapperProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<ECharts | null>(null);
  const resolvedTheme = useUIStore((s) => s.resolvedTheme);

  const echartsTheme = resolvedTheme === "dark" ? ECHARTS_DARK_THEME : ECHARTS_LIGHT_THEME;

  // Initialize or reinitialize chart when theme changes
  useEffect(() => {
    if (!containerRef.current) return;

    // Dispose existing chart
    if (chartRef.current) {
      chartRef.current.dispose();
    }

    // Create new chart with current theme
    chartRef.current = echarts.init(containerRef.current, echartsTheme, {
      renderer: "canvas",
    });

    chartRef.current.setOption(option);

    return () => {
      chartRef.current?.dispose();
      chartRef.current = null;
    };
  }, [echartsTheme]); // Reinit on theme change

  // Update options when they change
  useEffect(() => {
    if (chartRef.current) {
      chartRef.current.setOption(option, { notMerge: true });
    }
  }, [option]);

  // Handle resize
  useEffect(() => {
    if (!containerRef.current || !chartRef.current) return;

    const resizeObserver = new ResizeObserver(() => {
      chartRef.current?.resize();
    });

    resizeObserver.observe(containerRef.current);
    return () => resizeObserver.disconnect();
  }, []);

  return <div ref={containerRef} className={className} style={style} />;
}

export const EChartWrapper = memo(EChartWrapperInner);
```

## Modify App.tsx

**File:** `frontend/src/App.tsx`

Change the import:
```typescript
// OLD
import { registerPulseDarkTheme } from "@/lib/charts/theme";
registerPulseDarkTheme();

// NEW
import { registerPulseThemes } from "@/lib/charts/theme";
registerPulseThemes();
```

## Verification

```bash
cd /home/opsconductor/simcloud/frontend && npm run build
```

## Files

| Action | File |
|--------|------|
| MODIFY | `frontend/src/lib/charts/theme.ts` |
| MODIFY | `frontend/src/lib/charts/EChartWrapper.tsx` |
| MODIFY | `frontend/src/App.tsx` |
