# Prompt 004 — Assemble NOCPage + Wire Route + Nav

Read `frontend/src/app/router.tsx` and `frontend/src/components/layout/AppSidebar.tsx`.

## Create `frontend/src/features/operator/noc/NOCPage.tsx`

Full operator NOC command center page combining all three components.

### Layout:
```
┌─────────────────────────────────────────────────────────────┐
│  NOC  ● HEALTHY    [Refresh interval: 15s ▾] [⏸] [↗]       │
│  Last updated: 14:32:01  │  10 tenants  │  247 devices     │
├─────────────────────────────────────────────────────────────┤
│  [ GaugeRow — 4 circular gauges ]                           │
├─────────────────────────────────────────────────────────────┤
│  [ MetricsChartGrid — 2×2 time series charts ]              │
├─────────────────────────────────────────────────────────────┤
│  [ ServiceTopologyStrip — pipeline health ]                 │
└─────────────────────────────────────────────────────────────┘
```

### Page wrapper:
```typescript
// Dark background for the NOC page specifically
<div className="min-h-screen bg-gray-950 text-gray-100 p-4 space-y-4">
```

### Header bar:
```typescript
<div className="flex items-center justify-between">
  <div className="flex items-center gap-4">
    <div className="flex items-center gap-2">
      <span className="text-lg font-bold tracking-wider text-gray-100">NOC</span>
      <StatusDot status={systemStatus} />
      <span className="text-sm text-gray-400">{systemStatus.toUpperCase()}</span>
    </div>
    <div className="text-xs text-gray-500">
      Last updated: {lastUpdated} &nbsp;|&nbsp;
      {aggregates?.tenants?.active} tenants &nbsp;|&nbsp;
      {aggregates?.devices?.registered} devices
    </div>
  </div>
  <div className="flex items-center gap-2">
    <select onChange={...} className="bg-gray-800 border-gray-600 text-gray-300 text-xs rounded px-2 py-1">
      <option value={15000}>15s</option>
      <option value={30000}>30s</option>
      <option value={60000}>60s</option>
    </select>
    <button onClick={togglePause} title="Pause/Resume" ...>
      {isPaused ? <Play /> : <Pause />}
    </button>
    <button onClick={enterFullscreen} title="Fullscreen" ...>
      <Maximize2 className="h-4 w-4" />
    </button>
  </div>
</div>
```

### Full-screen button:
```typescript
const enterFullscreen = () => {
  document.documentElement.requestFullscreen?.();
};
```

### Pass `refreshInterval` and `isPaused` as props to child components
so they can use `refetchInterval: isPaused ? false : refreshInterval`.

## Wire route:
In `frontend/src/app/router.tsx`:
- Import NOCPage
- Add `{ path: 'noc', element: <NOCPage /> }` under the operator route children

## Wire nav:
In `frontend/src/components/layout/AppSidebar.tsx`:
- In the operator nav Overview group, add:
  `{ label: 'NOC', href: '/operator/noc', icon: Monitor }`
- Place it first in the group, above System Metrics

## Acceptance Criteria
- [ ] NOCPage.tsx assembles GaugeRow + MetricsChartGrid + ServiceTopologyStrip
- [ ] Dark bg-gray-950 background
- [ ] Header shows system status, last updated, tenant/device counts
- [ ] Refresh interval selector (15s/30s/60s)
- [ ] Pause/resume button
- [ ] Fullscreen button calls requestFullscreen
- [ ] Route /operator/noc wired
- [ ] NOC nav item added to operator sidebar
- [ ] `npm run build` passes
