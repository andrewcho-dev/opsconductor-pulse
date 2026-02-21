# Phase 79e — Hide /customer/users UI for non-tenant-admin users

## Problem

`GET /customer/users` requires `tenant-admin` Keycloak role.
The frontend renders the Users page/nav link for all authenticated users,
causing a 403 for users with only the `customer` role.

## Fix

### Step 1: Find where the Users nav link is rendered

Search for the nav link or route that points to `/app/users` or `/users`
in the sidebar or nav component. It will be in one of:
- `frontend/src/components/layout/AppSidebar.tsx`
- `frontend/src/app/router.tsx`

### Step 2: Check how the current user's roles are exposed

Look for a `useAuth`, `useUser`, or similar hook that returns the user's
Keycloak token claims. The `realm_access.roles` array contains the roles.

Example pattern to look for:
```typescript
const { user } = useAuth();
const roles = user?.realm_access?.roles ?? [];
const isTenantAdmin = roles.includes('tenant-admin') || roles.includes('operator') || roles.includes('operator-admin');
```

### Step 3: Gate the Users nav link

Wrap the Users nav item in a conditional so it only renders for tenant-admin or operator:

```typescript
{isTenantAdmin && (
  <NavItem href="/app/users" label="Users" icon={...} />
)}
```

### Step 4: Gate the Users route

In `router.tsx`, wrap the Users route with a role check that redirects to `/app/dashboard`
(or shows a 403 page) if the user lacks the `tenant-admin` role.

### Step 5: Build check

```bash
cd frontend && npm run build 2>&1 | tail -10
```

### Step 6: Commit and push

```bash
git add -A
git commit -m "Hide Users page from non-tenant-admin users to prevent 403 on load"
git push origin main
git log --oneline -3
```

## Report

- Where the nav link was found
- What role check pattern was used
- Build status
- Confirm Users link no longer visible when logged in as `customer` role user
