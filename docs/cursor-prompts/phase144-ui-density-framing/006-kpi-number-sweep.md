# Task 6: Standardize KPI Numbers to text-2xl font-semibold

## Context

KPI/stat numbers use 5 different sizes. The rule: ALL KPI numbers use `text-2xl font-semibold`. No exceptions.

## Exact Changes

### text-5xl → text-2xl

**File:** `frontend/src/features/operator/SystemMetricsPage.tsx:171`
```
BEFORE: <div className="text-5xl font-semibold">{deliveryFailures}</div>
AFTER:  <div className="text-2xl font-semibold">{deliveryFailures}</div>
```

### text-3xl → text-2xl

**File:** `frontend/src/features/dashboard/FleetKpiStrip.tsx:143`
```
BEFORE: <div className="mt-1 text-3xl font-bold">{card.value}</div>
AFTER:  <div className="mt-1 text-2xl font-semibold">{card.value}</div>
```

**File:** `frontend/src/features/dashboard/widgets/StatCardsWidget.tsx:33`
```
BEFORE: <div className="text-3xl font-bold">{value}</div>
AFTER:  <div className="text-2xl font-semibold">{value}</div>
```

**File:** `frontend/src/features/dashboard/widgets/renderers/KpiTileRenderer.tsx:108`
```
BEFORE: <div className="text-3xl font-bold">{value}</div>
AFTER:  <div className="text-2xl font-semibold">{value}</div>
```

**File:** `frontend/src/features/dashboard/widgets/renderers/DeviceCountRenderer.tsx:25`
```
BEFORE: <div className="text-3xl font-bold">{(total ?? 0).toLocaleString()}</div>
AFTER:  <div className="text-2xl font-semibold">{(total ?? 0).toLocaleString()}</div>
```

**File:** `frontend/src/features/devices/UptimeSummaryWidget.tsx:15`
```
BEFORE: <div className="text-3xl font-semibold">{(data?.avg_uptime_pct ?? 0).toFixed(1)}%</div>
AFTER:  <div className="text-2xl font-semibold">{(data?.avg_uptime_pct ?? 0).toFixed(1)}%</div>
```

### text-2xl font-bold → text-2xl font-semibold

These are already the right size but need weight fix. Run:
```bash
grep -rn "text-2xl font-bold" frontend/src/ --include="*.tsx"
```

For EACH match, change `font-bold` to `font-semibold`:

- `frontend/src/features/analytics/AnalyticsPage.tsx` — 4 instances (lines 382, 390, 398, 406)
- `frontend/src/features/operator/OperatorTenantDetailPage.tsx` — 4 instances (lines 155, 168, 182, 195)
- `frontend/src/features/operator/SubscriptionInfoCards.tsx` — 1 instance (line 26)
- `frontend/src/features/operator/CertificateOverviewPage.tsx` — 4 instances (lines 155, 159, 163, 167)
- `frontend/src/features/dashboard/widgets/FleetHealthWidget.tsx` — 1 instance (line 92)
- `frontend/src/features/dashboard/widgets/renderers/HealthScoreRenderer.tsx` — 1 instance (line 76)

### text-4xl → text-2xl

**File:** `frontend/src/features/NotFoundPage.tsx:9`

Keep this one at `text-4xl` — the 404 page is intentionally dramatic.

## Verify

```bash
# Should return 0 results for text-3xl, text-5xl in features/
grep -rn "text-3xl\|text-5xl" frontend/src/features/ --include="*.tsx" | wc -l

# text-2xl should all be font-semibold (not font-bold)
grep -rn "text-2xl font-bold" frontend/src/features/ --include="*.tsx" | wc -l
# Should be 0

cd frontend && npx tsc --noEmit
```
