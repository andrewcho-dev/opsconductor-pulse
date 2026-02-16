# 009 — End-to-End Verification

## Task

Verify the entire IAM permission system works end-to-end. This is a manual verification checklist — no code to write.

## Prerequisites

- Migration 080 has been applied: `python db/migrate.py`
- Backend is running with the new middleware and routes
- Frontend is built and served

## Verification Steps

### 1. Migration Verification

```sql
-- Connect to the database and verify:
SELECT COUNT(*) FROM permissions;
-- Expected: 28

SELECT name, is_system FROM roles WHERE is_system = true ORDER BY name;
-- Expected: 6 rows: Alert Manager, Device Manager, Full Admin, Integration Manager, Team Admin, Viewer

SELECT r.name, COUNT(rp.permission_id) as perm_count
FROM roles r
JOIN role_permissions rp ON rp.role_id = r.id
WHERE r.is_system = true
GROUP BY r.name
ORDER BY r.name;
-- Expected:
-- Alert Manager: 15
-- Device Manager: 15
-- Full Admin: 28
-- Integration Manager: 13
-- Team Admin: 15
-- Viewer: 11

SELECT COUNT(*) FROM user_role_assignments;
-- Expected: 0 (no assignments yet — auto-bootstrap happens on first request)
```

### 2. Auto-Bootstrap Verification

**Test with tenant-admin user (customer1):**
1. Log in as customer1 (has `tenant-admin` Keycloak realm role)
2. Navigate to any customer page (triggers `inject_permissions`)
3. Check DB:
```sql
SELECT ura.user_id, r.name
FROM user_role_assignments ura
JOIN roles r ON r.id = ura.role_id;
-- Expected: customer1's sub → "Full Admin"
```
4. Call `GET /customer/me/permissions` (browser DevTools → Network tab)
   - Expected: all 28 permissions returned

**Test with regular customer user (customer2):**
1. Log in as customer2 (has `customer` Keycloak realm role)
2. Navigate to dashboard
3. Check DB:
   - Expected: customer2's sub → "Viewer"
4. Call `GET /customer/me/permissions`
   - Expected: 11 read-only permissions

### 3. Permission Enforcement

**As customer2 (Viewer only):**
- `GET /customer/users` → should return 403 "Permission required: users.read"
  - Wait — Viewer has `users.read`. So this should succeed.
  - Actually check: does Viewer have `users.read`? Yes, it's one of the `*.read` permissions.
  - So `GET /customer/users` should succeed for Viewer
  - But `POST /customer/users/invite` should return 403 (requires `users.invite`)
  - And `DELETE /customer/users/{id}` should return 403 (requires `users.remove`)

**Correct test for 403:**
- Create a custom role with ONLY `dashboard.read` permission
- Assign it to a test user (removing Viewer)
- That user should get 403 on `GET /customer/users` (lacks `users.read`)

### 4. Role Assignment

**As customer1 (Full Admin):**
1. Go to Team page (`/users`)
2. Click "Manage Roles" on customer2
3. Dialog should show:
   - Current assignments (Viewer checked)
   - All system roles available
4. Check "Device Manager" in addition to Viewer
5. Click Save
6. Verify:
   - `GET /customer/users/CUSTOMER2_ID/assignments` shows 2 assignments
   - customer2 now has Viewer + Device Manager permissions (union)
   - customer2 can now access device write endpoints

### 5. Custom Role Creation

**As customer1:**
1. Go to Roles page (`/roles`)
2. Click "+ New Role"
3. Enter name: "Monitoring Lead"
4. Select permissions: `alerts.*` (all 5 alert permissions) + `maintenance.*` (2 permissions) + all `*.read` permissions
5. Click Create
6. Verify:
   - Role appears in Custom Roles section
   - Permission count shows correctly
   - Expanding shows all selected permissions
7. Assign this custom role to customer2 via Team → Manage Roles
8. Verify customer2 has the union of Viewer + Device Manager + Monitoring Lead permissions

### 6. Custom Role Edit/Delete

**Edit:**
1. Click "Edit" on "Monitoring Lead" custom role
2. Add `integrations.write` permission
3. Save
4. Verify the role's permission count increased
5. Verify users assigned to this role now have `integrations.write`

**Delete:**
1. Click "Delete" on "Monitoring Lead"
2. Confirm deletion
3. Verify:
   - Role removed from list
   - Users who had this role lose those permissions
   - Their other role assignments still work

### 7. Sidebar Gating

**As a user with only Viewer role:**
- Settings section should show: Subscription, Notification Prefs
- "Team" should be visible (Viewer has `users.read`)
- "Roles" should NOT be visible (Viewer lacks `users.roles`)

**As a user with Team Admin role:**
- "Team" visible (has `users.read`)
- "Roles" visible (has `users.roles`)

### 8. Route Guards

**As a user without `users.read`:**
- Navigate directly to `/users` → should redirect to `/dashboard`

**As a user without `users.roles`:**
- Navigate directly to `/roles` → should redirect to `/dashboard`

### 9. Operator Bypass

**As operator1:**
1. Log in (has `operator` realm role)
2. Verify:
   - No auto-bootstrap happens (operators skip permission system)
   - `GET /customer/me/permissions` returns `["*"]` or all permissions
   - Can access all customer endpoints
   - Sidebar shows all items
   - Can manage roles and assignments

### 10. System Role Protection

**As customer1 (Full Admin):**
- `PUT /customer/roles/{viewer_role_id}` → 403 "Cannot modify system roles"
- `DELETE /customer/roles/{viewer_role_id}` → 403 "Cannot delete system roles"
- In the UI: system roles should not have Edit/Delete buttons (or they should be disabled)

### 11. Self-Modification Guard

**As customer1:**
- Try to change own roles via Manage Roles dialog
- Backend should return 400 "Cannot change own roles"
- UI should prevent this (disabled or hidden for self)

### 12. Backward Compatibility

- Existing users who were already logged in before the migration should auto-bootstrap on their next request
- No manual data migration needed
- Keycloak realm roles still work for authentication (login/token)
- Operator portal (`/operator/*`) is completely unaffected

## Troubleshooting

| Symptom | Likely cause |
|---------|-------------|
| 403 on all customer endpoints | `inject_permissions` not in dependency chain |
| Auto-bootstrap not happening | `bootstrap_user_roles` not finding system roles (check NULL tenant_id query) |
| Permissions empty after bootstrap | RLS policy on `role_permissions` blocking reads (shouldn't happen since no RLS on that table) |
| Sidebar not updating after role change | `refetchPermissions()` not called after save |
| `/roles` page blank | Route not added to router, or RolesPage import missing |
| System roles editable | `is_system` check missing in PUT/DELETE endpoints |
