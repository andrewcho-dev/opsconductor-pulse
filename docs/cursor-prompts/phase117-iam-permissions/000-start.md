# Phase 117 — AWS IAM-Style Granular Permission System

## Overview

Replace the binary User/Admin role system with a granular, AWS IAM-style permission system. Keycloak stays for authentication; all authorization moves to PostgreSQL managed from the Pulse UI.

**Core principle:** Keycloak realm roles (`customer`, `tenant-admin`, `operator`, `operator-admin`) gate entry. Fine-grained permission checks happen against Pulse DB tables. Operators bypass the permission system entirely.

## Execution Order

Execute prompts in this order — each builds on the previous:

| # | File | What it does | Depends on |
|---|------|--------------|------------|
| 1 | `001-migration.md` | SQL migration 080: 4 new tables + seed data + RLS | Nothing |
| 2 | `002-permissions-middleware.md` | Backend `middleware/permissions.py` — ContextVar, loader, guard factory, auto-bootstrap | #1 |
| 3 | `003-roles-api.md` | Backend `routes/roles.py` — CRUD for roles/permissions + mount in `app.py` | #1, #2 |
| 4 | `004-guard-migration.md` | Replace 7 inline `"tenant-admin"` checks in `users.py` with permission guards | #2 |
| 5 | `005-permission-provider.md` | Frontend `PermissionProvider` + `usePermissions()` hook | #3 |
| 6 | `006-manage-roles-dialog.md` | Replace `ChangeRoleDialog` with multi-role assignment dialog | #3, #5 |
| 7 | `007-roles-page.md` | Roles management page + permission grid + custom role builder | #3, #5 |
| 8 | `008-sidebar-guards.md` | Update sidebar + route guards to use permission checks | #5 |
| 9 | `009-verify.md` | End-to-end verification steps | All above |

## Key Architecture Decisions

- **Operator bypass**: `is_operator()` → skip all permission checks, grant full access
- **Auto-bootstrap**: First request where user has Keycloak roles but no DB assignments → auto-assign system role (`tenant-admin` → Full Admin, `customer` → Viewer)
- **System roles are immutable**: 6 predefined roles cannot be edited/deleted
- **Custom roles are tenant-scoped**: Each tenant can create their own role bundles
- **28 atomic permissions**: Organized by category (devices, alerts, users, etc.)
- **Multi-role assignment**: Users can have multiple roles; effective permissions = union of all assigned role permissions

## Files Created/Modified

### New Files
- `db/migrations/080_iam_permissions.sql`
- `services/ui_iot/middleware/permissions.py`
- `services/ui_iot/routes/roles.py`
- `frontend/src/services/auth/PermissionProvider.tsx`
- `frontend/src/features/users/ManageUserRolesDialog.tsx`
- `frontend/src/features/roles/RolesPage.tsx`
- `frontend/src/features/roles/CreateRoleDialog.tsx`
- `frontend/src/features/roles/PermissionGrid.tsx`
- `frontend/src/hooks/use-roles.ts`
- `frontend/src/services/api/roles.ts`

### Modified Files
- `services/ui_iot/app.py` (line 180 area — mount new router)
- `services/ui_iot/routes/users.py` (lines 658, 688, 725, 794, 831, 879, 926 — replace tenant-admin checks)
- `frontend/src/services/auth/AuthProvider.tsx` (wrap with PermissionProvider)
- `frontend/src/services/auth/types.ts` (add permission types)
- `frontend/src/services/auth/index.ts` (re-export)
- `frontend/src/components/layout/AppSidebar.tsx` (lines 110-114, 146-150 — permission-based visibility)
- `frontend/src/features/users/UsersPage.tsx` (use ManageUserRolesDialog instead of ChangeRoleDialog)
- `frontend/src/app/router.tsx` (lines 59-68, 109-112 — replace RequireTenantAdminOrOperator, add roles route)
