# Prompt 002 — Frontend: Tenant List + Create Modal

Read `frontend/src/features/operator/` — find the existing operator dashboard page.
Read `frontend/src/services/api/operator.ts` (just created).

## Create `frontend/src/features/operator/TenantListPage.tsx`

A page showing all tenants in a table:

Columns:
- Tenant ID (monospace)
- Name
- Status (badge: ACTIVE=green, SUSPENDED=red, other=grey)
- Created At (formatted date)
- Actions: "View" button → navigates to `/operator/tenants/:tenantId`

Features:
- Status filter dropdown (ALL / ACTIVE / SUSPENDED)
- Pagination (limit 50)
- "Create Tenant" button (top right) → opens CreateTenantModal

## Create `frontend/src/features/operator/CreateTenantModal.tsx`

A modal with form:
- **Name** (required, text input)
- Any other fields the POST /operator/tenants endpoint accepts (check the API)

On submit: calls `createTenant(data)`, closes modal, refetches tenant list.
On error: shows inline error.

## Acceptance Criteria

- [ ] TenantListPage.tsx exists with table, status filter, pagination
- [ ] CreateTenantModal.tsx exists
- [ ] "Create Tenant" button opens modal
- [ ] After create, list refetches
- [ ] `npm run build` passes
