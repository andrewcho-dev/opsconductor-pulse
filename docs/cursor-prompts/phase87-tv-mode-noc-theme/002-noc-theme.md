# Prompt 002 — ECharts Dark Theme Registration + NOC Color Tokens

Read `frontend/src/lib/charts/EChartWrapper.tsx` to understand how ECharts
is initialized.

## Register a unified ECharts NOC dark theme

In `frontend/src/lib/charts/nocTheme.ts` (new file):

```typescript
import * as echarts from 'echarts';

// NOC dark theme for all operator charts
export const NOC_THEME_NAME = 'noc-dark';

export function registerNocTheme() {
  echarts.registerTheme(NOC_THEME_NAME, {
    backgroundColor: 'transparent',
    textStyle: { color: '#9ca3af' },
    title: { textStyle: { color: '#e5e7eb' } },
    legend: { textStyle: { color: '#9ca3af' } },
    tooltip: {
      backgroundColor: '#1f2937',
      borderColor: '#374151',
      textStyle: { color: '#f3f4f6' },
    },
    line: { itemStyle: { borderWidth: 2 } },
    categoryAxis: {
      axisLine: { lineStyle: { color: '#374151' } },
      axisTick: { lineStyle: { color: '#374151' } },
      axisLabel: { color: '#6b7280' },
      splitLine: { lineStyle: { color: '#1f2937' } },
    },
    valueAxis: {
      axisLine: { lineStyle: { color: '#374151' } },
      axisLabel: { color: '#6b7280' },
      splitLine: { lineStyle: { color: '#1f2937', type: 'dashed' } },
    },
  });
}
```

In `frontend/src/main.tsx` (or app entry point), call `registerNocTheme()` once on startup.

## Update MetricsChartGrid to use the NOC theme

In `MetricsChartGrid.tsx`, pass `theme={NOC_THEME_NAME}` to each EChartWrapper
instead of the string `'dark'`.

## NOC color tokens

In `frontend/src/features/operator/noc/nocColors.ts` (new file):
```typescript
export const NOC_COLORS = {
  healthy: '#22c55e',
  warning: '#f59e0b',
  critical: '#ef4444',
  info: '#3b82f6',
  neutral: '#6b7280',
  ingest: '#3b82f6',
  alerts: '#ef4444',
  queue: '#f59e0b',
  db: '#8b5cf6',
  bg: {
    page: '#030712',      // gray-950
    card: '#111827',      // gray-900
    cardBorder: '#1f2937' // gray-800
  }
} as const;
```

Import NOC_COLORS in GaugeRow, MetricsChartGrid, ServiceTopologyStrip, AlertHeatmap,
LiveEventFeed and replace all hardcoded hex color strings with these tokens.

## Acceptance Criteria
- [ ] nocTheme.ts exports and registers NOC dark theme
- [ ] registerNocTheme() called in main.tsx
- [ ] MetricsChartGrid uses NOC_THEME_NAME
- [ ] nocColors.ts exports NOC_COLORS
- [ ] Color tokens used consistently in NOC components
- [ ] `npm run build` passes
