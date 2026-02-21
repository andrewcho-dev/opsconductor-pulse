# Task 8: Cap Empty State Padding

## Context

Empty states (placeholder text when no data exists) use excessive vertical padding — up to `py-20` (80px). This wastes space and makes the UI feel hollow. Cap at `py-8` maximum.

## Step 1: Fix EmptyState component

**File:** `frontend/src/components/shared/EmptyState.tsx`

```
BEFORE: <div className="flex flex-col items-center justify-center py-12 text-center">
AFTER:  <div className="flex flex-col items-center justify-center py-8 text-center">
```

## Step 2: Fix inline empty states

Run: `grep -rn "py-12\|py-16\|py-20" frontend/src/ --include="*.tsx"`

For each match, reduce to `py-8`:

Known instances:
- `frontend/src/features/analytics/AnalyticsPage.tsx:372` — `py-20` → `py-8`
- `frontend/src/features/dashboard/DashboardPage.tsx:90` — `py-20` → `py-8`
- `frontend/src/features/dashboard/DashboardBuilder.tsx:155` — `py-20` → `py-8`
- `frontend/src/features/settings/BillingPage.tsx:140` — `py-12` → `py-8`
- `frontend/src/features/settings/ProfilePage.tsx:71` — `py-12` → `py-8`
- `frontend/src/features/settings/OrganizationPage.tsx:107` — `py-12` → `py-8`
- `frontend/src/features/users/UsersPage.tsx:239` — `py-12` → `py-8`
- `frontend/src/features/operator/OperatorUsersPage.tsx:172` — `py-12` → `py-8`

## Step 3: Check for py-8 in non-empty-state contexts

After the sweep, `py-8` should only appear in empty state / placeholder contexts. If you find `py-8` on a normal content container, reduce it to `py-4`.

## Checkpoint

```bash
cd frontend && npx tsc --noEmit
```
