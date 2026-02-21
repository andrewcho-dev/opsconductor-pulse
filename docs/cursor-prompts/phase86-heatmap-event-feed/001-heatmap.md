# Prompt 001 — Alert Volume Heatmap

Read `frontend/src/features/operator/noc/NOCPage.tsx` and
`frontend/src/features/operator/SystemMetricsPage.tsx`.

## Create `frontend/src/features/operator/noc/AlertHeatmap.tsx`

An ECharts heatmap showing alert volume by day-of-week × hour-of-day.

### Data source:
Fetch GET /operator/system/aggregates (already includes alert data).
For the heatmap, fetch GET /operator/alerts?limit=200 (operator-level alert list).
Transform: group alerts by `dayOfWeek` (0-6) and `hourOfDay` (0-23), count per cell.

```typescript
// Transform alerts into heatmap data
const heatmapData = useMemo(() => {
  if (!alerts) return [];
  const counts: Record<string, number> = {};
  alerts.forEach(alert => {
    const date = new Date(alert.created_at);
    const day = date.getDay(); // 0=Sun
    const hour = date.getHours();
    const key = `${day}-${hour}`;
    counts[key] = (counts[key] || 0) + 1;
  });
  // Return as [hour, day, count] for ECharts heatmap
  return Array.from({ length: 7 }, (_, day) =>
    Array.from({ length: 24 }, (_, hour) => [hour, day, counts[`${day}-${hour}`] || 0])
  ).flat();
}, [alerts]);
```

### ECharts heatmap option:
```typescript
const heatmapOption: echarts.EChartsOption = {
  backgroundColor: 'transparent',
  tooltip: {
    position: 'top',
    formatter: (p: any) => `${DAYS[p.data[1]]} ${p.data[0]}:00 — ${p.data[2]} alerts`,
  },
  grid: { left: 60, right: 20, top: 30, bottom: 40 },
  xAxis: {
    type: 'category',
    data: Array.from({ length: 24 }, (_, i) => `${i}:00`),
    axisLabel: { color: '#6b7280', fontSize: 9, interval: 2 },
    splitArea: { show: false },
  },
  yAxis: {
    type: 'category',
    data: ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'],
    axisLabel: { color: '#6b7280', fontSize: 10 },
    splitArea: { show: false },
  },
  visualMap: {
    min: 0,
    max: 10,
    calculable: true,
    orient: 'horizontal',
    left: 'center',
    bottom: 0,
    inRange: {
      color: ['#1f2937', '#1e3a5f', '#1d4ed8', '#3b82f6', '#ef4444'],
    },
    textStyle: { color: '#6b7280', fontSize: 9 },
  },
  series: [{
    type: 'heatmap',
    data: heatmapData,
    label: { show: false },
    emphasis: { itemStyle: { shadowBlur: 10, shadowColor: 'rgba(0,0,0,0.5)' } },
  }],
};
```

### Component:
- Dark card: `bg-gray-900 border-gray-700`
- Title: "Alert Volume — Last 7 Days (by hour)"
- Height: `h-52`
- Fetch alerts from GET /operator/alerts?limit=200 with `refetchInterval: 60000`
- Show total alert count in subtitle: "X alerts in last 7 days"

## Acceptance Criteria
- [ ] AlertHeatmap.tsx renders ECharts heatmap
- [ ] Data grouped by day-of-week × hour-of-day
- [ ] Color scale from dark (0) to red (high)
- [ ] Tooltip shows day/hour/count on hover
- [ ] `npm run build` passes
