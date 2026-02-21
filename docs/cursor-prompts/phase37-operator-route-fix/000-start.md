# Phase 37: Fix Operator Access to Customer Routes

## Problem Summary

Operator users get 401 errors on `/api/v2/*` endpoints because:
1. Customer routes (`/dashboard`, `/devices`, etc.) lack role-based protection
2. These routes call tenant-scoped APIs (`/api/v2/fleet/summary`, `/api/v2/devices`)
3. Operators don't have `organization`/`tenant_id` claims → backend returns 401

## Solution

Add a `RequireCustomer` route wrapper (mirroring the existing `RequireOperator`) and apply it to all customer routes. This prevents operators from accessing customer-only pages.

## Execution Order

1. `001-add-require-customer.md` — Add RequireCustomer component and restructure routes

## Files Modified

- `frontend/src/app/router.tsx` — Add RequireCustomer, restructure route nesting

## Verification

After applying the fix:
1. Login as operator → should redirect to `/operator` dashboard
2. Manually navigate to `/dashboard` → should redirect back to `/operator`
3. No 401 errors on page load
