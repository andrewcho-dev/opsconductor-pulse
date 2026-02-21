# Prompt 003 — Add Heatmap + Event Feed to NOCPage

Read `frontend/src/features/operator/noc/NOCPage.tsx` after Phase 84.

## Add a new bottom row to NOCPage

Import AlertHeatmap and LiveEventFeed.
Add a side-by-side row below the ServiceTopologyStrip:

```typescript
{/* Bottom row: heatmap + event feed */}
<div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
  <AlertHeatmap refreshInterval={refreshInterval} isPaused={isPaused} />
  <LiveEventFeed refreshInterval={10000} isPaused={isPaused} />
</div>
```

Pass `isPaused` prop to both components so they respect the global pause toggle.
When `isPaused` is true: `refetchInterval: false`.

## Acceptance Criteria
- [ ] AlertHeatmap and LiveEventFeed appear in NOCPage below topology strip
- [ ] Both respect isPaused prop
- [ ] `npm run build` passes
