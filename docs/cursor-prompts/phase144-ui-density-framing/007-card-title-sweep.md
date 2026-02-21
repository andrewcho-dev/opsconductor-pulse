# Task 7: Remove Ad-Hoc CardTitle Size Overrides

## Context

The CardTitle component has a base className of `text-sm leading-none font-semibold`. But many files override this with `text-lg` or `text-base`, creating inconsistency. The rule: card titles are always `text-sm font-semibold`. No overrides.

## Step 1: Remove text-lg overrides

Run: `grep -rn 'CardTitle className="text-lg' frontend/src/ --include="*.tsx"`

For each match, remove the `text-lg` from the className. The CardTitle component already has `text-sm` as default.

Known instances:
- `frontend/src/features/devices/MetricGaugesSection.tsx:31` — `<CardTitle className="text-lg">` → `<CardTitle>`
- `frontend/src/features/dashboard/widgets/AlertStreamWidget.tsx:35` — `<CardTitle className="text-lg">` → `<CardTitle>`
- `frontend/src/features/devices/DeviceAlertsSection.tsx:31` — `<CardTitle className="text-lg">` → `<CardTitle>`
- `frontend/src/features/dashboard/widgets/DeviceTableWidget.tsx:24` — `<CardTitle className="text-lg">` → `<CardTitle>`
- `frontend/src/features/operator/SettingsPage.tsx:134` — `<CardTitle className="text-lg">` → `<CardTitle>`
- `frontend/src/features/operator/SettingsPage.tsx:220` — `<CardTitle className="text-lg">` → `<CardTitle>`

## Step 2: Remove text-base overrides

Run: `grep -rn 'CardTitle className="text-base' frontend/src/ --include="*.tsx"`

For each match, remove the `text-base` from the className. If there are additional classes (like `flex items-center gap-2`), keep those but remove the size class.

Known instances:
- `frontend/src/features/settings/BillingPage.tsx` — 3 instances: `<CardTitle className="text-base flex items-center gap-2">` → `<CardTitle className="flex items-center gap-2">`
- `frontend/src/features/settings/ProfilePage.tsx` — 3 instances: same pattern
- `frontend/src/features/settings/OrganizationPage.tsx` — 3 instances: same pattern
- `frontend/src/features/dashboard/widgets/FleetHealthWidget.tsx` — 2 instances: `<CardTitle className="text-base">` → `<CardTitle>`
- `frontend/src/components/shared/OnboardingChecklist.tsx` — 1 instance
- `frontend/src/features/operator/OperatorTenantDetailPage.tsx` — 1 instance
- `frontend/src/features/operator/DeviceTiersPage.tsx` — 1 instance

## Step 3: Verify no size overrides remain

```bash
grep -rn 'CardTitle className="text-' frontend/src/ --include="*.tsx"
```

The only remaining matches should be `text-sm font-medium` patterns (which are acceptable since they match the base size).

## Checkpoint

```bash
cd frontend && npx tsc --noEmit
```
