# Phase 26.7: Frontend Debug Logging

## Task

Add console logging to see exactly what data the frontend receives.

## Add Logging

**File:** `frontend/src/hooks/use-device-telemetry.ts`

Add console.log after fetching REST data:

```typescript
// After REST data is fetched
useEffect(() => {
  if (restData?.telemetry) {
    console.log('[telemetry] REST response:', {
      count: restData.telemetry.length,
      sample: restData.telemetry.slice(0, 2),
    });

    const metrics = discoverMetrics(restData.telemetry);
    console.log('[telemetry] discovered metrics:', metrics);

    if (restData.telemetry.length > 0) {
      console.log('[telemetry] first point metrics:', restData.telemetry[0].metrics);
      console.log('[telemetry] first point metric types:',
        Object.entries(restData.telemetry[0].metrics || {}).map(([k, v]) => `${k}: ${typeof v}`)
      );
    }
  }
}, [restData]);
```

**File:** `frontend/src/lib/charts/transforms.ts`

Add logging in `discoverMetrics()`:

```typescript
export function discoverMetrics(points: TelemetryPoint[]): string[] {
  const metricSet = new Set<string>();

  for (const point of points) {
    if (point.metrics) {
      for (const [key, value] of Object.entries(point.metrics)) {
        console.log(`[discoverMetrics] key=${key} value=${value} type=${typeof value}`);
        if (typeof value === "number") {
          metricSet.add(key);
        }
      }
    }
  }

  const result = Array.from(metricSet).sort();
  console.log('[discoverMetrics] result:', result);
  return result;
}
```

## Rebuild and Test

```bash
cd /home/opsconductor/simcloud/frontend && npm run build
cp -r dist/* ../services/ui_iot/spa/
cd ../compose && docker compose restart ui
```

Open browser DevTools → Console, load device detail page.

Report what you see:
- Are metrics arriving?
- What types are the values? (number vs string)
- What does discoverMetrics return?

## Files

| File | Action |
|------|--------|
| `frontend/src/hooks/use-device-telemetry.ts` | Add console logging |
| `frontend/src/lib/charts/transforms.ts` | Add logging in discoverMetrics |
