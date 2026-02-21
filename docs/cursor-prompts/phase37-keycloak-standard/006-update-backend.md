# 006: Update Backend to Use Organizations

## Task

Update the backend to read tenant ID from the organization claim instead of user attributes.

## Token Structure

After the Keycloak changes, tokens will contain:

```json
{
  "sub": "user-uuid",
  "preferred_username": "acme-admin",
  "organization": {
    "acme-industrial": {}
  },
  "realm_access": {
    "roles": ["customer", "tenant-admin", "default-roles-pulse"]
  }
}
```

## Files to Modify

### 1. Auth Utilities

**File:** `services/ui_iot/auth.py` (or wherever `get_tenant_id()` is defined)

Find the function that extracts tenant_id from the token and update it:

```python
# OLD (attribute-based)
def get_tenant_id() -> Optional[str]:
    """Get tenant ID from current user's token."""
    user = get_user()
    if not user:
        return None
    return user.get("tenant_id")


# NEW (organization-based)
def get_tenant_id() -> Optional[str]:
    """Get tenant ID from current user's organization membership."""
    user = get_user()
    if not user:
        return None

    # Check for organization claim
    orgs = user.get("organization", {})
    if orgs:
        # User belongs to an organization - use the first one as tenant_id
        # The org alias IS the tenant_id (e.g., "acme-industrial")
        return list(orgs.keys())[0]

    # Operators don't have organization - they're system-wide
    return None


def get_user_organizations() -> dict:
    """Get all organizations the user belongs to."""
    user = get_user()
    if not user:
        return {}
    return user.get("organization", {})


def is_operator() -> bool:
    """Check if current user is a system operator (no organization)."""
    user = get_user()
    if not user:
        return False

    roles = get_user_roles()
    return "operator" in roles or "operator-admin" in roles


def get_user_roles() -> list:
    """Get user's realm roles from token."""
    user = get_user()
    if not user:
        return []

    # Roles are in realm_access.roles
    realm_access = user.get("realm_access", {})
    return realm_access.get("roles", [])


def has_role(role: str) -> bool:
    """Check if user has a specific role."""
    return role in get_user_roles()
```

### 2. Route Guards

**File:** `services/ui_iot/routes/customer.py`

Update any tenant checks:

```python
# OLD
async def require_tenant_admin():
    user = get_user()
    tenant_id = get_tenant_id()
    if not user:
        raise HTTPException(401, "Not authenticated")
    # Custom attribute check...


# NEW
async def require_tenant_admin():
    """Verify current user has tenant-admin role within their organization."""
    user = get_user()
    if not user:
        raise HTTPException(401, "Not authenticated")

    roles = get_user_roles()

    # Operators can manage any tenant
    if "operator" in roles or "operator-admin" in roles:
        return True

    # Must have tenant-admin role
    if "tenant-admin" not in roles:
        raise HTTPException(403, "Tenant admin role required")

    # Must belong to an organization
    tenant_id = get_tenant_id()
    if not tenant_id:
        raise HTTPException(403, "No organization membership")

    return True
```

### 3. Operator Routes

**File:** `services/ui_iot/routes/operator.py`

Update operator checks:

```python
# Ensure operator routes check for operator role
async def require_operator():
    """Verify current user is a system operator."""
    if not is_operator():
        raise HTTPException(403, "Operator role required")
    return True


async def require_operator_admin():
    """Verify current user is an operator admin."""
    if not has_role("operator-admin"):
        raise HTTPException(403, "Operator admin role required")
    return True
```

### 4. Frontend Token Parsing

**File:** `frontend/src/hooks/use-auth.ts` (or similar)

Update to read organization:

```typescript
// OLD
interface User {
  sub: string;
  preferred_username: string;
  tenant_id?: string;
  role?: string;
}

// NEW
interface User {
  sub: string;
  preferred_username: string;
  email?: string;
  organization?: Record<string, object>;  // { "acme-industrial": {} }
  realm_access?: {
    roles: string[];
  };
}

// Helper to get tenant ID
function getTenantId(user: User): string | null {
  if (!user.organization) return null;
  const orgs = Object.keys(user.organization);
  return orgs.length > 0 ? orgs[0] : null;
}

// Helper to check roles
function hasRole(user: User, role: string): boolean {
  return user.realm_access?.roles?.includes(role) ?? false;
}

function isOperator(user: User): boolean {
  return hasRole(user, 'operator') || hasRole(user, 'operator-admin');
}

function isTenantAdmin(user: User): boolean {
  return hasRole(user, 'tenant-admin');
}
```

### 5. Sidebar/Navigation

**File:** `frontend/src/components/layout/AppSidebar.tsx`

Update navigation visibility based on roles:

```typescript
// Show operator menu items only for operators
const showOperatorMenu = isOperator(user);

// Show tenant admin menu items for tenant-admins
const showTenantAdminMenu = isTenantAdmin(user) || isOperator(user);

// Get tenant for display
const tenantId = getTenantId(user);
const isSystemUser = !tenantId && isOperator(user);
```

## Search and Replace Guide

Find these patterns and update:

| Old Pattern | New Pattern |
|-------------|-------------|
| `user.get("tenant_id")` | `get_tenant_id()` or `list(user.get("organization", {}).keys())[0]` |
| `user.get("role")` | `get_user_roles()` or `user.get("realm_access", {}).get("roles", [])` |
| `token.tenant_id` | `getTenantId(user)` |
| `token.role` | `user.realm_access?.roles` |

## Verification

After updating, test with both user types:

```bash
# Test as tenant user
curl -H "Authorization: Bearer $ACME_ADMIN_TOKEN" https://localhost/customer/devices
# Should return only acme-industrial devices

# Test as operator
curl -H "Authorization: Bearer $OPERATOR_TOKEN" https://localhost/operator/tenants
# Should return all tenants
```
