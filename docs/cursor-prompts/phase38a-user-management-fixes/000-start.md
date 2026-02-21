# Phase 38a: User Management Bug Fixes

## Issues Found in Testing

1. **HIGH** - Missing email/name in created users
2. **HIGH** - Tenant badge not showing in operator UI after assignment
3. **MEDIUM** - Self-targeting actions visible in menus
4. **MEDIUM** - Role badge inconsistency after change (stale data)

## Execution Order

1. `001-fix-user-create-data.md` - Fix user creation to preserve and return full profile
2. `002-fix-tenant-badge-sync.md` - Sync org membership with tenant_id attribute
3. `003-hide-self-actions.md` - Hide self-targeting actions in UI
4. `004-fix-role-refresh.md` - Force refetch after role changes

## Files Modified

- `services/ui_iot/services/keycloak_admin.py`
- `services/ui_iot/routes/users.py`
- `frontend/src/features/operator/OperatorUsersPage.tsx`
- `frontend/src/features/users/UsersPage.tsx`
- `frontend/src/hooks/use-users.ts`
