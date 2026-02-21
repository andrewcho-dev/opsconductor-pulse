# Prompt 002 — Per-Tenant Row: Sparkline + Health Bar

Read `frontend/src/features/operator/TenantHealthMatrix.tsx` after Prompt 001.

## Enhance each tenant row with a mini activity sparkline

### Create `frontend/src/features/operator/TenantActivitySparkline.tsx`

Props: `{ tenantId: string; height?: number }`

Fetches GET /operator/tenants/{tenantId}/stats and renders a tiny SVG sparkline
showing device count trend or alert count over last 24h (use whatever time-series
data is available from the stats endpoint).

If no time-series data is available from that endpoint, use a static horizontal
line at the current online device count.

Render as a 60×24px inline SVG (same Sparkline pattern as SystemDashboard.tsx).

### Add sparkline column to TenantHealthMatrix:

Add a "ACTIVITY" column between Devices and Device Health:

```
│ TENANT    │ DEVICES │ ACTIVITY │ DEVICE HEALTH │ ALERTS │ ...
│ acme-corp │  24/30  │ ╱‾‾╲╱‾  │ ████░░ 80%   │ ⚠ 3   │ ...
```

Sparkline width: ~80px, height: 24px.

### Health bar component:

Create a reusable `TenantHealthBar` component:

```typescript
function TenantHealthBar({ onlinePct }: { onlinePct: number }) {
  const color = onlinePct >= 90 ? '#22c55e' : onlinePct >= 70 ? '#f59e0b' : '#ef4444';
  return (
    <div className="flex items-center gap-2">
      <div className="w-24 h-2 bg-gray-200 dark:bg-gray-700 rounded overflow-hidden">
        <div className="h-full rounded transition-all" style={{ width: `${onlinePct}%`, backgroundColor: color }} />
      </div>
      <span className="text-xs tabular-nums" style={{ color }}>{onlinePct.toFixed(0)}%</span>
    </div>
  );
}
```

## Acceptance Criteria
- [ ] TenantActivitySparkline.tsx renders for each row
- [ ] TenantHealthBar shows colored progress bar
- [ ] Activity column added to matrix
- [ ] `npm run build` passes
