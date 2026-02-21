# Prompt 006 — Verify Phase 64

## Step 1: Unit Tests

```bash
pytest -m unit -v 2>&1 | tail -40
```

## Step 2: TypeScript Build

```bash
cd frontend && npm run build 2>&1 | tail -10
```

## Step 3: Checklist

### Backend
- [ ] GET /operator/users exists
- [ ] GET /operator/users/{id} returns user + roles
- [ ] POST /operator/users creates user
- [ ] PATCH /operator/users/{id} updates user
- [ ] DELETE /operator/users/{id} deletes user
- [ ] POST /operator/users/{id}/reset-password
- [ ] POST /operator/users/{id}/send-password-reset
- [ ] POST/DELETE /operator/users/{id}/roles/{role}

### Frontend
- [ ] UserListPage.tsx at /operator/users
- [ ] UserDetailPage.tsx at /operator/users/:userId
- [ ] "Users" nav link
- [ ] Create user modal
- [ ] Role management (add/remove)
- [ ] Set password form

### Unit Tests
- [ ] test_keycloak_user_mgmt.py with 11 tests

## Report

Output PASS / FAIL per criterion.
