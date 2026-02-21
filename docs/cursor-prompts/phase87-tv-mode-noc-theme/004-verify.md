# Prompt 004 — Verify Phase 87

## Step 1
```bash
cd frontend && npm run build 2>&1 | tail -20
```

## Checklist
- [ ] F key toggles TV mode (sidebar hides, fullscreen enters)
- [ ] Escape exits TV mode
- [ ] TV MODE badge visible in top-right when active
- [ ] nocTheme.ts registered at app startup
- [ ] MetricsChartGrid uses noc-dark theme
- [ ] NOC_COLORS tokens used across all NOC components
- [ ] OperatorDashboard shows KPI cards + 4 nav cards + error feed
- [ ] npm run build passes

## Step 2: Commit and push
```bash
git add -A
git commit -m "Phase 87: TV mode, NOC dark theme polish, operator landing page redesign

- TV mode: F key toggles fullscreen + hides sidebar, Escape exits
- NOC dark theme: registered echarts theme + NOC_COLORS token system
- OperatorDashboard: redesigned as command center landing with KPI cards,
  nav cards to NOC/Matrix/Tenants, recent errors feed"
git push origin main
git log --oneline -3
```
