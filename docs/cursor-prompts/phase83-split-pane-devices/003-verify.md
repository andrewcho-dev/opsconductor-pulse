# Prompt 003 — Verify Phase 83

## Step 1
```bash
cd frontend && npm run build 2>&1 | tail -20
```

## Checklist
- [ ] DeviceListPage shows split-pane on lg+ screens
- [ ] Left pane: search, status filter, site filter, status dots, alert badge
- [ ] Selecting device highlights row and shows DeviceDetailPane
- [ ] DeviceDetailPane has 5 tabs: Overview, Telemetry, Alerts, Tokens, Uptime
- [ ] Tokens tab uses DeviceApiTokensPanel (no duplication)
- [ ] Uptime tab uses DeviceUptimePanel (no duplication)
- [ ] Edit opens EditDeviceModal
- [ ] Mobile: click navigates to DeviceDetailPage
- [ ] npm run build passes

## Step 2: Commit and push
```bash
git add -A
git commit -m "Phase 83: Split-pane device list with tabbed detail panel (AWS console pattern)

- DeviceListPage: split-pane on lg+ screens (list left, detail right)
- Left pane: search, status/site filters, status dots, open alert badges
- DeviceDetailPane: 5 tabs (Overview, Telemetry, Alerts, Tokens, Uptime)
- Reuses DeviceApiTokensPanel, DeviceUptimePanel, telemetry chart components
- Mobile: retains existing navigate-to-detail behavior"
git push origin main
git log --oneline -3
```
