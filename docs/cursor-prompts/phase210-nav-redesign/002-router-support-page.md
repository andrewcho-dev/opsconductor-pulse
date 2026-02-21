# Task 2: Add Support Route + Reports Route

## Files to modify
- `frontend/src/app/router.tsx`
- New file: `frontend/src/features/support/SupportPage.tsx`
- New file: `frontend/src/features/reports/ReportsPage.tsx`

## Read first
Read `frontend/src/app/router.tsx` in full.

## Step 1 — Create SupportPage

Create `frontend/src/features/support/SupportPage.tsx`:

- Simple page with a `PageHeader` titled "Support"
- Two sections:
  1. **Contact Support** — email link and/or a form link (placeholder for now)
  2. **Documentation** — links to /docs or external documentation site (use "#" as placeholder)
- Use the existing `Card` and `PageHeader` components
- Keep it simple — this is a placeholder that can be expanded later

## Step 2 — Create ReportsPage

Create `frontend/src/features/reports/ReportsPage.tsx`:

- Simple page with a `PageHeader` titled "Reports"
- Show an `EmptyState` component indicating reports are coming soon
- Use the existing `EmptyState` component pattern from the codebase

## Step 3 — Add routes to router.tsx

In the customer routes section (inside `RequireCustomer`), add:

```tsx
{ path: "support", element: <SupportPage /> },
{ path: "reports", element: <ReportsPage /> },
```

Import the new page components at the top of router.tsx.

## After changes
Run: `cd frontend && npm run build 2>&1 | tail -20`
Fix any TypeScript or import errors.
