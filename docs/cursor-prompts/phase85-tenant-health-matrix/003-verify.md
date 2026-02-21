# Prompt 003 — Verify Phase 85

## Step 1
```bash
cd frontend && npm run build 2>&1 | tail -20
```

## Checklist
- [ ] /operator/tenant-matrix loads with all tenants
- [ ] Device health bar colored by online %
- [ ] Alert count colored (gray/yellow/red)
- [ ] Activity sparkline per row
- [ ] Sort by Alerts/Devices/LastActive/Name works
- [ ] Search filters tenant list
- [ ] Row click → TenantDetailPage
- [ ] Nav link "Health Matrix" in operator sidebar
- [ ] npm run build passes

## Step 2: Commit and push
```bash
git add -A
git commit -m "Phase 85: Tenant health matrix with device health bars, alert counts, sparklines

- TenantHealthMatrix: dense operator view of all tenant health
- Columns: tenant, devices, activity sparkline, health bar, alerts, last active, status
- Sort by alerts/devices/activity/name, client-side search
- Row click navigates to TenantDetailPage
- Route /operator/tenant-matrix + sidebar nav link"
git push origin main
git log --oneline -3
```
