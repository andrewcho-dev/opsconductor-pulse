# Prompt 005 — Verify Phase 84

## Step 1
```bash
cd frontend && npm run build 2>&1 | tail -20
```

## Checklist
- [ ] /operator/noc route loads without errors
- [ ] 4 ECharts gauge dials in top row with correct colors
- [ ] 4 time-series charts in 2×2 grid with dark theme
- [ ] ServiceTopologyStrip shows all 6 pipeline services with status colors
- [ ] Header shows system status + last updated + counts
- [ ] Refresh interval selector works
- [ ] Fullscreen button works
- [ ] NOC link in operator sidebar
- [ ] npm run build passes

## Step 2: Commit and push
```bash
git add -A
git commit -m "Phase 84: NOC command center page with gauge dials, time-series charts, service topology

- GaugeRow: 4 ECharts circular gauges (fleet online%, ingest rate, open alerts, DB conn%)
- MetricsChartGrid: 4 dark time-series charts (ingest, alert rate, queue depth, DB conns)
- ServiceTopologyStrip: pipeline health visualization with status-colored nodes
- NOCPage: full dark bg-gray-950 layout with refresh control and fullscreen button
- Route /operator/noc wired, NOC link in operator sidebar"
git push origin main
git log --oneline -3
```
