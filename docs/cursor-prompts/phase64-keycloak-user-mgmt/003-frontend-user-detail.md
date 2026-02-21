# Prompt 003 — Frontend: UserDetailPage + Role Management

## Create `frontend/src/features/operator/UserDetailPage.tsx`

Route: `/operator/users/:userId`

Sections:
1. **User Profile** — username, email, name, enabled status, email verified badge. "Edit" button → PATCH fields inline or modal.
2. **Roles** — list of assigned realm roles. "Add Role" button → dropdown of available roles (GET /operator/roles or known roles: customer, operator, admin). "Remove" button per role.
3. **Password Actions** — "Set Password" button → form with password + temporary toggle. "Send Reset Email" button.

## Add API Functions in `operator.ts`

```typescript
export async function fetchUserDetail(userId: string): Promise<KeycloakUser> {
  return apiFetch(`/operator/users/${userId}`);
}

export async function updateUser(userId: string, updates: Partial<{
  first_name: string; last_name: string; enabled: boolean; email_verified: boolean;
}>): Promise<void> {
  await apiFetch(`/operator/users/${userId}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(updates),
  });
}

export async function resetUserPassword(userId: string, password: string, temporary: boolean): Promise<void> {
  await apiFetch(`/operator/users/${userId}/reset-password`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ password, temporary }),
  });
}

export async function assignRole(userId: string, roleName: string): Promise<void> {
  await apiFetch(`/operator/users/${userId}/roles/${roleName}`, { method: 'POST' });
}

export async function removeRole(userId: string, roleName: string): Promise<void> {
  await apiFetch(`/operator/users/${userId}/roles/${roleName}`, { method: 'DELETE' });
}
```

## Acceptance Criteria

- [ ] UserDetailPage.tsx at /operator/users/:userId
- [ ] Shows profile, roles, password actions
- [ ] Edit profile works (PATCH)
- [ ] Add/remove role works
- [ ] Set password form with temporary toggle
- [ ] Send reset email button
- [ ] `npm run build` passes
