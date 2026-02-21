# Prompt 004 — Verify Phase 86

## Step 1
```bash
cd frontend && npm run build 2>&1 | tail -20
```

## Checklist
- [ ] Alert heatmap renders in NOCPage bottom-left
- [ ] Heatmap shows day×hour grid with color intensity
- [ ] Live event feed renders in NOCPage bottom-right
- [ ] Event feed shows color-coded events with timestamps
- [ ] Both components respect isPaused
- [ ] npm run build passes

## Step 2: Commit and push
```bash
git add -A
git commit -m "Phase 86: Alert volume heatmap and live event feed added to NOC page

- AlertHeatmap: ECharts day×hour heatmap of alert density (blue→red scale)
- LiveEventFeed: scrolling monospace event stream with color-coded severity
- Both wired into NOCPage bottom row, respect global pause toggle"
git push origin main
git log --oneline -3
```
