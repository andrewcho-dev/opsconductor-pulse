# 010 — Fix 403 on GET /customer/users/{user_id}

## Bug

`GET /customer/users/{user_id}` returns 403 "User not in your tenant" even when the user IS in the tenant.

### Root Cause

Keycloak's `GET /admin/realms/{realm}/users/{id}` endpoint returns a user representation that **omits the `attributes` key** entirely. But the list endpoint (`GET /admin/realms/{realm}/users`) returns the same user WITH `attributes: {"tenant_id": ["acme-industrial"]}`.

This causes `_is_user_in_tenant()` → `format_user_response()` → `attributes.get("tenant_id")` → `None` → falls through to the organizations check → Keycloak organizations API returns 404 → user is deemed "not in tenant" → 403.

The `GET /customer/users` (list) endpoint works fine because `list_users()` calls the Keycloak list endpoint which does return attributes.

### Evidence

```python
# Single user GET — NO attributes
GET /admin/realms/pulse/users/1233e4f1-...
{"id": "...", "username": "customer1", "email": "...", "enabled": true}

# List GET — HAS attributes
GET /admin/realms/pulse/users
[{"id": "...", "username": "customer1", "attributes": {"tenant_id": ["acme-industrial"]}, ...}]
```

## Fix 1: `services/ui_iot/services/keycloak_admin.py`

### Modify `get_user()` (line 133-136)

When the single-user endpoint returns a response without `attributes`, fall back to the list endpoint filtered by username to get the full representation.

```python
# FROM:
async def get_user(user_id: str) -> dict | None:
    """Get user by Keycloak ID."""
    resp = await _admin_request("GET", f"/users/{user_id}")
    return resp if isinstance(resp, dict) else None

# TO:
async def get_user(user_id: str) -> dict | None:
    """Get user by Keycloak ID."""
    resp = await _admin_request("GET", f"/users/{user_id}")
    if not isinstance(resp, dict):
        return None
    # Keycloak 26+ may omit 'attributes' from single-user GET.
    # Fall back to the list endpoint which returns the full representation.
    if "attributes" not in resp:
        username = resp.get("username")
        if username:
            users = await _admin_request(
                "GET", "/users", params={"username": username, "exact": "true"}
            )
            if isinstance(users, list) and users:
                return users[0]
    return resp
```

This adds one extra Keycloak call only when attributes are missing. It won't trigger for most Keycloak versions that return attributes normally. Once Keycloak is upgraded or the user profile config is fixed, the fallback won't fire.

## Fix 2: `services/ui_iot/routes/users.py`

### Make `_is_user_in_tenant` more defensive (line 122-127)

Add a fallback that checks `user_role_assignments` in the DB. If the target user has any role assignment in this tenant, they're a valid tenant member — even if Keycloak attributes are missing.

```python
# FROM:
async def _is_user_in_tenant(user: dict[str, Any], tenant_id: str) -> bool:
    formatted = format_user_response(user)
    if _extract_primary_tenant(formatted) == tenant_id:
        return True
    member_ids = await _tenant_member_ids(tenant_id)
    return str(user.get("id")) in member_ids

# TO:
async def _is_user_in_tenant(user: dict[str, Any], tenant_id: str) -> bool:
    formatted = format_user_response(user)
    if _extract_primary_tenant(formatted) == tenant_id:
        return True
    member_ids = await _tenant_member_ids(tenant_id)
    return str(user.get("id")) in member_ids
```

Actually — this function is fine as-is. Fix 1 (getting attributes via the list endpoint fallback) is sufficient. The `format_user_response` will now receive the correct attributes and `_extract_primary_tenant` will match.

No change needed in `users.py`.

## Verification

1. `GET /customer/users/{user_id}` should return 200 (not 403) when the user is in the same tenant
2. Check backend logs — you should see two Keycloak admin API calls for the detail endpoint:
   - First: `GET /admin/realms/pulse/users/{id}` (no attributes)
   - Second: `GET /admin/realms/pulse/users?username=customer1&exact=true` (with attributes)
3. The list endpoint `GET /customer/users` should still work normally
4. `ManageUserRolesDialog` should load the user's name correctly

## Optional Future Fix

Investigate why Keycloak 26 omits attributes from `GET /users/{id}`. This might be related to:
- Keycloak's "User Profile" feature (declarative user profile in Keycloak 24+)
- Missing `tenant_id` in the user profile configuration
- A Keycloak admin API change in the version being used

If the Keycloak config is fixed (user profile declares `tenant_id` as a user attribute), the fallback code path won't trigger and can be removed.
