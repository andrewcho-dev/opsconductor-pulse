# Phase 38: User Management UI

## Problem Summary

The system has no user management UI. Users can only be created/managed directly in Keycloak admin console, which is not viable for production:

- Tenant admins cannot invite/remove users for their organization
- Operators cannot manage users across tenants
- No way to assign roles, view user lists, or disable accounts from the app

## Solution

Build user management features at two levels:

1. **Operator-level** (`/operator/users`) - Cross-tenant user management
2. **Tenant-level** (`/users`) - Tenant-scoped user management for admins

## Architecture

### Backend
- New service: `services/ui_iot/services/keycloak_admin.py` - Keycloak Admin API client
- New routes: `/operator/users/*` - Operator user management
- New routes: `/customer/users/*` - Tenant user management
- Audit logging for all user operations

### Frontend
- New page: `OperatorUsersPage.tsx` - List/manage all users
- New page: `UsersPage.tsx` - Tenant user management
- Dialogs: Create user, edit user, invite user, assign role

## Keycloak Integration

**Admin API Access:**
- URL: `KEYCLOAK_INTERNAL_URL` (http://pulse-keycloak:8080)
- Realm: `pulse`
- Admin credentials via env vars: `KEYCLOAK_ADMIN_USERNAME`, `KEYCLOAK_ADMIN_PASSWORD`

**User Attributes:**
- `tenant_id` - Array of tenant IDs user belongs to
- Realm roles: `customer`, `tenant-admin`, `operator`, `operator-admin`

**Organizations:**
- Keycloak 26.0 has Organizations feature enabled
- Users are assigned to organizations which map to tenants

## Execution Order

1. `001-keycloak-admin-service.md` - Backend Keycloak Admin API service
2. `002-operator-user-routes.md` - Backend operator routes
3. `003-customer-user-routes.md` - Backend tenant routes
4. `004-operator-users-frontend.md` - Frontend operator page
5. `005-customer-users-frontend.md` - Frontend tenant page

## Files Created/Modified

### New Files
- `services/ui_iot/services/keycloak_admin.py`
- `services/ui_iot/routes/users.py`
- `frontend/src/features/operator/OperatorUsersPage.tsx`
- `frontend/src/features/operator/CreateUserDialog.tsx`
- `frontend/src/features/operator/EditUserDialog.tsx`
- `frontend/src/features/users/UsersPage.tsx`
- `frontend/src/features/users/InviteUserDialog.tsx`
- `frontend/src/services/api/users.ts`
- `frontend/src/hooks/use-users.ts`

### Modified Files
- `services/ui_iot/app.py` - Register new routes
- `compose/docker-compose.yml` - Add admin credential env vars
- `frontend/src/app/router.tsx` - Add user routes
- `frontend/src/components/layout/AppSidebar.tsx` - Add navigation items

## Environment Variables

Add to docker-compose.yml ui service:
```yaml
KEYCLOAK_ADMIN_USERNAME: "${KEYCLOAK_ADMIN_USERNAME:-admin}"
KEYCLOAK_ADMIN_PASSWORD: "${KEYCLOAK_ADMIN_PASSWORD:-admin_dev}"
```

## Verification

After implementation:
1. Login as operator-admin → navigate to `/operator/users`
2. Create a new user with customer role
3. Assign user to a tenant
4. Login as tenant-admin → navigate to `/users`
5. See only users in own tenant
6. Invite a new user to the tenant
