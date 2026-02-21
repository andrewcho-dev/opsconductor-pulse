# Prompt 002 — Frontend: UserListPage

Read `frontend/src/features/operator/TenantListPage.tsx` for table/layout patterns.
Read `frontend/src/services/api/operator.ts` for API client patterns.

## Add API Functions in `frontend/src/services/api/operator.ts`

```typescript
export interface KeycloakUser {
  id: string;
  username: string;
  email: string;
  firstName?: string;
  lastName?: string;
  enabled: boolean;
  emailVerified: boolean;
  createdTimestamp?: number;
  roles?: string[];
}

export async function fetchUsers(params?: {
  search?: string; first?: number; max?: number;
}): Promise<{ users: KeycloakUser[]; total: number }> {
  const qs = new URLSearchParams(params as any).toString();
  return apiFetch(`/operator/users${qs ? '?' + qs : ''}`);
}

export async function createUser(data: {
  username: string; email: string;
  first_name?: string; last_name?: string;
  temporary_password: string; enabled?: boolean;
}): Promise<KeycloakUser> {
  return apiFetch('/operator/users', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
}

export async function deleteUser(userId: string): Promise<void> {
  await apiFetch(`/operator/users/${userId}`, { method: 'DELETE' });
}

export async function sendPasswordReset(userId: string): Promise<void> {
  await apiFetch(`/operator/users/${userId}/send-password-reset`, { method: 'POST' });
}
```

## Create `frontend/src/features/operator/UserListPage.tsx`

Table columns:
- Username (link to `/operator/users/:userId`)
- Email
- Name (firstName + lastName)
- Enabled (green/red badge)
- Email Verified (badge)
- Actions: "View" button, "Send Password Reset" button

Features:
- Search input (debounced 300ms) → passes to `?search=` param
- "Create User" button → opens CreateUserModal (inline or separate component)
- After create/delete: refetch

## Create User Modal

Fields:
- Username (required)
- Email (required)
- First Name (optional)
- Last Name (optional)
- Temporary Password (required, min 8 chars)

## Acceptance Criteria

- [ ] UserListPage.tsx exists with table and search
- [ ] Create user modal with required fields
- [ ] Send password reset button per row
- [ ] `npm run build` passes
