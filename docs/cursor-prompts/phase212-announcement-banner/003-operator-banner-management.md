# Task 3: Operator Banner Management UI

## Files to create/modify
- New: `frontend/src/features/operator/BroadcastsPage.tsx`
- Modify: `frontend/src/app/router.tsx` — add operator broadcasts route
- Modify: `frontend/src/components/layout/AppSidebar.tsx` — add broadcasts to operator nav

## Read first
Read the existing operator pages (e.g. `frontend/src/features/operator/TenantsPage.tsx`)
to understand the pattern used for operator CRUD pages.

## Step 1 — BroadcastsPage

Create `frontend/src/features/operator/BroadcastsPage.tsx`:

A simple CRUD page for managing broadcasts and banner announcements.

### Layout
- `PageHeader` titled "Broadcasts & Announcements"
- Two tabs: "News Broadcasts" and "Banner Announcements"
- Each tab shows a data table of broadcasts filtered by `is_banner`

### News Broadcasts tab (is_banner = false)
Columns: Title | Type | Active | Pinned | Created | Actions (Edit, Delete)

### Banner Announcements tab (is_banner = true)
Columns: Title | Type | Active | Created | Expires | Actions (Edit, Delete)
Note: only one banner is shown at a time (the most recent active one). Show a callout explaining this.

### Create/Edit dialog
Dialog with fields:
- Title (text input, required)
- Body (textarea, required)
- Type (select: info / warning / update / critical)
- Active toggle (switch)
- Pinned toggle (switch, news only)
- Is Banner toggle (switch)
- Expires At (date picker, optional)

### API calls
Use existing `apiFetch` pattern:
- GET `/api/v1/operator/broadcasts` — list all
- POST `/api/v1/operator/broadcasts` — create
- PATCH `/api/v1/operator/broadcasts/{id}` — update
- DELETE `/api/v1/operator/broadcasts/{id}` — delete

Use React Query with `invalidateQueries(["operator-broadcasts"])` after mutations.

## Step 2 — Add to operator router
In `router.tsx` inside the operator routes section, add:
```tsx
{ path: "broadcasts", element: <BroadcastsPage /> }
```

## Step 3 — Add to operator sidebar
In `AppSidebar.tsx` operator nav section, add a "Broadcasts" item under the System group
with a `Radio` or `Megaphone` icon pointing to `/operator/broadcasts`.

## After changes
Run: `cd frontend && npm run build 2>&1 | tail -20`
