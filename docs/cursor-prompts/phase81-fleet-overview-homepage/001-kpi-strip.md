# Prompt 001 — KPI Strip Component

Read `frontend/src/features/dashboard/DashboardPage.tsx` and the existing widget
files in `frontend/src/features/dashboard/widgets/` before making changes.

## Create `frontend/src/features/dashboard/FleetKpiStrip.tsx`

A horizontal row of 6 KPI cards. Each card has: icon, number (large), label (small),
and a trend indicator or status color.

Data sources (all already exist):
1. **Total Devices** — from GET /customer/devices/summary or /api/v2/fleet/summary `.total`
2. **Online** — fleet summary `.online` — green color
3. **Offline** — fleet summary `.offline` — red if > 0, else gray
4. **Fleet Uptime %** — from GET /customer/fleet/uptime-summary `.avg_uptime_pct` — color: green ≥99%, yellow ≥95%, red <95%
5. **Open Alerts** — from GET /customer/alerts?status=OPEN&limit=1 `.total` — red if > 0
6. **Active Maintenance** — from GET /customer/maintenance-windows, count where is_active=true — blue

Each card uses a colored left border (4px) matching its semantic color.
Cards auto-refresh every 30 seconds.

Props: none (fetches own data)

```typescript
// Example card structure
<div className="flex-1 border rounded-lg p-4 border-l-4 border-l-green-500">
  <div className="flex items-center justify-between">
    <span className="text-sm text-muted-foreground">Online</span>
    <Wifi className="h-4 w-4 text-green-500" />
  </div>
  <div className="text-3xl font-bold mt-1">{online}</div>
</div>
```

## Acceptance Criteria
- [ ] FleetKpiStrip.tsx renders 6 KPI cards in a responsive horizontal row
- [ ] Colors update based on values (green/yellow/red/blue)
- [ ] Auto-refreshes every 30s
- [ ] `npm run build` passes
