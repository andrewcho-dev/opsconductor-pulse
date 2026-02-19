# Task 3: MetricsPage Deprecation

## Modify file: `frontend/src/features/metrics/MetricsPage.tsx`

### Add Deprecation Banner

At the top of the MetricsPage component, add a deprecation notice banner:

```tsx
<div className="mb-6 rounded-lg border border-yellow-200 bg-yellow-50 p-4 dark:border-yellow-800 dark:bg-yellow-950">
  <div className="flex items-center gap-2">
    <AlertTriangle className="h-5 w-5 text-yellow-600 dark:text-yellow-400" />
    <h3 className="font-semibold text-yellow-800 dark:text-yellow-200">Legacy Page</h3>
  </div>
  <p className="mt-1 text-sm text-yellow-700 dark:text-yellow-300">
    Metric definitions are now managed through{" "}
    <a href="/app/templates" className="underline font-medium">Device Templates</a>.
    This page shows legacy metric catalog and normalized metrics for reference only.
    No new entries should be created here.
  </p>
</div>
```

Import `AlertTriangle` from `lucide-react`.

### Make Read-Only

If the MetricsPage currently has Create/Edit/Delete controls for `metric_catalog` or `normalized_metrics`:
1. Hide or disable the "Create" button
2. Hide or disable "Edit" and "Delete" actions on existing rows
3. Keep the data display functional for reference

### Backend: Add deprecation headers (optional)

If the backend metrics endpoints exist, add deprecation headers:

```python
response.headers["Deprecation"] = "true"
response.headers["Sunset"] = "2026-06-01"
response.headers["Link"] = '</api/v1/customer/templates>; rel="successor-version"'
```

## Verification

1. MetricsPage renders with deprecation banner
2. Create/Edit/Delete controls are hidden or disabled
3. Existing metric data is still readable
4. Link in banner navigates to Templates page
