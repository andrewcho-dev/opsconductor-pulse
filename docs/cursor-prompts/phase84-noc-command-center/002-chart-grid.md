# Prompt 002 — Middle: 4 Time-Series Charts

Read `frontend/src/features/operator/SystemMetricsPage.tsx` to understand
existing ECharts time-series patterns.

## Create `frontend/src/features/operator/noc/MetricsChartGrid.tsx`

Four ECharts time-series charts in a 2×2 grid. Each chart:
- Dark background: `bg-gray-900 border-gray-700`
- Height: `h-52`
- ECharts theme: dark (`echarts.init(dom, 'dark')`) — pass `theme="dark"` to EChartWrapper
- Tooltip on hover showing time + value
- No legend (title is enough)

### Chart 1: Ingest Rate (top-left)
- Title: "Message Ingestion Rate"
- API: GET /operator/system/metrics/history?metric=messages_written&minutes=60&service=ingest&rate=true
- Y-axis: "msg/s"
- Series: smooth line, color: #3b82f6 (blue)
- Area fill below line (areaStyle with opacity 0.15)

### Chart 2: Alert Fire Rate (top-right)
- Title: "Alert Fire Rate"
- API: GET /operator/system/metrics/history?metric=alerts_open&minutes=60&rate=true
- Y-axis: "alerts/min"
- Series: smooth line, color: #ef4444 (red)
- Area fill, opacity 0.15

### Chart 3: Queue Depth (bottom-left)
- Title: "Worker Queue Depth"
- API: GET /operator/system/metrics/history?metric=queue_depth&minutes=60
- Y-axis: "jobs"
- Series: step line (`step: 'end'`), color: #f59e0b (yellow)
- Area fill, opacity 0.15
- markLine at y=1000 (warning threshold): dashed gray

### Chart 4: DB Connections (bottom-right)
- Title: "Database Connections"
- API: GET /operator/system/metrics/history?metric=connections&minutes=60
- Y-axis: "connections"
- Series: smooth line, color: #8b5cf6 (purple)
- Area fill, opacity 0.15

### Data fetching:
Each chart fetches its own data with `useQuery` and `refetchInterval: 30000`.
Transform API response: `data.points.map(p => [new Date(p.time).getTime(), p.value])`

### Chart option template:
```typescript
const lineOption = (data: [number, number][], color: string, yName: string, stepped = false): echarts.EChartsOption => ({
  backgroundColor: 'transparent',
  tooltip: { trigger: 'axis', formatter: ... },
  grid: { left: 50, right: 20, top: 30, bottom: 40 },
  xAxis: { type: 'time', axisLabel: { color: '#6b7280', fontSize: 10 } },
  yAxis: { type: 'value', name: yName, nameTextStyle: { color: '#6b7280', fontSize: 10 }, axisLabel: { color: '#6b7280', fontSize: 10 } },
  series: [{
    type: 'line',
    smooth: !stepped,
    step: stepped ? 'end' : undefined,
    data,
    lineStyle: { color, width: 2 },
    itemStyle: { color },
    areaStyle: { color, opacity: 0.15 },
    showSymbol: false,
  }]
});
```

## Acceptance Criteria
- [ ] MetricsChartGrid.tsx with 4 dark ECharts time-series charts
- [ ] Each chart fetches its own metric from /operator/system/metrics/history
- [ ] Charts refresh every 30s
- [ ] Area fill on all charts
- [ ] Queue depth chart has warning markLine at 1000
- [ ] `npm run build` passes
