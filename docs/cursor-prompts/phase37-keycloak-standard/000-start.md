# Phase 37: Standardize Keycloak with Organizations

## Problem

Current Keycloak setup uses custom user attributes for multi-tenancy. This is:
- Non-standard
- Not properly isolated
- Broken (attributes showing as empty)
- Not using Keycloak's built-in Organizations feature

## Solution

Enable Keycloak Organizations feature and migrate to proper multi-tenancy:
- Each tenant = one Organization
- Users belong to Organizations (not attributes)
- Operators exist outside Organizations (system-wide)
- Standard Keycloak, no custom hacks

## Current State (from audit)

```
Realm: pulse
Keycloak: 24.0.5 (supports Organizations)
Organizations: NOT ENABLED (missing --features=organization)

Protocol Mappers (pulse-ui):
- tenant_id: attribute mapper (WRONG - should be org)
- role: attribute mapper (WRONG - should use realm roles)

Realm Roles:
- customer (only one created)
- Missing: operator, operator-admin, tenant-admin

Users:
- acme-admin, customer1, customer2, operator1, operator_admin
- All have EMPTY attributes
```

## Target State

```
Keycloak: 24.0.5 with --features=organization
Organizations: Enabled

Organizations:
- acme-industrial (Acme Industrial)

Realm Roles:
- operator (system-wide monitoring)
- operator-admin (system-wide admin)
- tenant-admin (manage org users)
- customer (standard org user)

Protocol Mappers (pulse-ui):
- organization: maps user's org membership to token
- realm_roles: maps realm roles to token

Users:
- operator1, operator_admin: NO org, have operator/operator-admin roles
- acme-admin: member of acme-industrial org, has tenant-admin role
- customer1, customer2: member of acme-industrial org, has customer role
```

## Execution Order

| # | File | Description |
|---|------|-------------|
| 1 | 001-enable-organizations.md | Add --features=organization to Keycloak startup |
| 2 | 002-create-roles.md | Create proper realm roles |
| 3 | 003-create-organization.md | Create acme-industrial Organization |
| 4 | 004-fix-protocol-mappers.md | Replace attribute mappers with org/role mappers |
| 5 | 005-migrate-users.md | Assign users to orgs and roles |
| 6 | 006-update-backend.md | Update backend to read org from token |
| 7 | 007-verify.md | End-to-end verification |

## Key Changes

### Docker Compose

```yaml
keycloak:
  command:
    - start-dev
    - --import-realm
    - --features=organization
```

### Token Claims (after fix)

```json
{
  "sub": "user-uuid",
  "preferred_username": "acme-admin",
  "organization": {
    "acme-industrial": {
      "name": "Acme Industrial",
      "roles": ["tenant-admin"]
    }
  },
  "realm_access": {
    "roles": ["customer", "tenant-admin"]
  }
}
```

### Backend Changes

```python
# OLD (attribute-based)
tenant_id = token.get("tenant_id")

# NEW (organization-based)
orgs = token.get("organization", {})
tenant_id = list(orgs.keys())[0] if orgs else None
```

## Rollback

If something breaks:
1. Remove `--features=organization` from docker-compose
2. Restart Keycloak
3. Users will still exist, just won't have org membership
