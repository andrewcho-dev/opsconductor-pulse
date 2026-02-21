# Prompt 001 — Top Row: 4 ECharts Gauge Dials

Read `frontend/src/features/operator/SystemMetricsPage.tsx` and
`frontend/src/features/operator/SystemDashboard.tsx` to understand existing
patterns before writing new components.

## Create `frontend/src/features/operator/noc/GaugeRow.tsx`

Four ECharts gauge dials in a horizontal row. Each gauge:
- Uses ECharts `gauge` series type
- Dark background card: `bg-gray-900 border-gray-700`
- Large bold value in center
- Colored arc (green/yellow/red based on thresholds)
- Label below the value

### Gauge 1: Fleet Online %
- Value: `(devices_online / devices_total) * 100`
- Data: from GET /operator/system/aggregates `.devices.online` / `.devices.registered`
- Thresholds: ≥95 green, ≥80 yellow, <80 red
- Max: 100, unit: "%"
- ECharts axisLine color segments: [[0.8, '#ef4444'], [0.95, '#f59e0b'], [1, '#22c55e']]

### Gauge 2: Ingest Rate (msg/s)
- Value: latest ingest rate from GET /operator/system/metrics/latest
- Look for `ingest.messages_written` or `ingest_rate` in the response
- Thresholds: any value is fine (blue gauge)
- Max: dynamically set to max(value * 1.5, 100)
- ECharts axisLine color: [[1, '#3b82f6']]

### Gauge 3: Open Alerts
- Value: from GET /operator/system/aggregates `.alerts.open`
- Thresholds: 0 green, 1-10 yellow, >10 red
- Max: dynamically set to max(value * 2, 50)
- ECharts axisLine color segments: [[0.2, '#22c55e'], [0.5, '#f59e0b'], [1, '#ef4444']]

### Gauge 4: DB Connection Usage %
- Value: from GET /operator/system/capacity `.postgres.connections_used / .postgres.connections_max * 100`
- Thresholds: <70 green, <90 yellow, ≥90 red
- Max: 100, unit: "%"
- ECharts axisLine color segments: [[0.7, '#22c55e'], [0.9, '#f59e0b'], [1, '#ef4444']]

### ECharts gauge option template:
```typescript
const gaugeOption = (value: number, max: number, colors: [number, string][], title: string, unit: string): echarts.EChartsOption => ({
  backgroundColor: 'transparent',
  series: [{
    type: 'gauge',
    min: 0,
    max,
    radius: '85%',
    axisLine: {
      lineStyle: {
        width: 12,
        color: colors,
      }
    },
    pointer: { itemStyle: { color: 'auto' }, length: '60%', width: 6 },
    axisTick: { show: false },
    splitLine: { length: 8, lineStyle: { color: 'auto', width: 2 } },
    axisLabel: { color: '#9ca3af', fontSize: 10, distance: 15 },
    detail: {
      valueAnimation: true,
      formatter: `{value}${unit}`,
      color: '#f3f4f6',
      fontSize: 22,
      fontWeight: 'bold',
      offsetCenter: [0, '65%'],
    },
    title: { color: '#6b7280', fontSize: 11, offsetCenter: [0, '90%'] },
    data: [{ value, name: title }],
  }]
});
```

### Data fetching:
Use `useQuery` with `refetchInterval: 15000` for all gauges.
All data fetched once at GaugeRow level, passed as props to each gauge.

### Layout:
```
<div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
  {gauges}
</div>
```
Each gauge card: `h-48` minimum, dark background.

## Acceptance Criteria
- [ ] GaugeRow.tsx with 4 ECharts gauge dials
- [ ] Colors change based on threshold values
- [ ] Refreshes every 15s
- [ ] Dark card backgrounds
- [ ] `npm run build` passes
