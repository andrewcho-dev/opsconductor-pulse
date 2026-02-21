# Fix Tenant Badge Visibility in Operator UI

## Problem

After assigning a user to a tenant via the operator UI, the tenant badge in the operator users table doesn't update. However, the user does appear in the tenant's `/users` list, indicating the org membership was successful.

## Root Cause

Two data sources are out of sync:
1. **Organization membership** - Used by tenant routes to check access (working)
2. **User attribute `tenant_id`** - Used by operator list to display badge (not updated)

The `assign_user_to_tenant()` route adds the user to the Keycloak organization but the `update_user()` call to set the `tenant_id` attribute may be failing silently or the attribute format is wrong.

## Fix

### 1. Update `services/ui_iot/routes/users.py` - `assign_user_to_tenant()`

Ensure the tenant_id attribute is properly set AND persisted:

```python
@router.post(
    "/operator/users/{user_id}/tenant",
    dependencies=[Depends(JWTBearer()), Depends(require_operator_admin)]
)
async def assign_user_to_tenant(user_id: str, request: AssignTenantRequest):
    """Assign a user to a tenant."""
    current_user = get_user()

    try:
        user = await kc_get_user(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # Get current attributes and update tenant_id
        attributes = user.get("attributes", {}) or {}
        attributes["tenant_id"] = [request.tenant_id]

        # Update user with new attributes - must send full user object
        await _admin_request("PUT", f"/users/{user_id}", json={
            "firstName": user.get("firstName", ""),
            "lastName": user.get("lastName", ""),
            "email": user.get("email", ""),
            "enabled": user.get("enabled", True),
            "attributes": attributes
        })

        # Also add to organization for proper membership
        try:
            orgs = await get_organizations()
            org = next((o for o in orgs if o.get("name") == request.tenant_id), None)
            if org:
                await add_user_to_organization(user_id, org["id"])
        except Exception as e:
            logger.warning(f"Could not add user to organization: {e}")

        # Audit log...

        return {"message": f"User assigned to tenant {request.tenant_id}"}
    except KeycloakAdminError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
```

### 2. Update `services/ui_iot/services/keycloak_admin.py` - `update_user()`

The current `update_user()` may not be handling attributes correctly. Fix it:

```python
async def update_user(user_id: str, updates: dict) -> None:
    """Update user attributes."""
    # First fetch current user to preserve existing data
    current_user = await get_user(user_id)
    if not current_user:
        raise KeycloakAdminError("User not found", 404)

    # Build update payload, merging with existing data
    user_data = {
        "firstName": updates.get("first_name", current_user.get("firstName", "")),
        "lastName": updates.get("last_name", current_user.get("lastName", "")),
        "email": updates.get("email", current_user.get("email", "")),
        "enabled": updates.get("enabled", current_user.get("enabled", True)),
    }

    # Handle attributes - merge rather than replace
    if "attributes" in updates:
        existing_attrs = current_user.get("attributes", {}) or {}
        merged_attrs = {**existing_attrs, **updates["attributes"]}
        user_data["attributes"] = merged_attrs
    else:
        user_data["attributes"] = current_user.get("attributes", {}) or {}

    await _admin_request("PUT", f"/users/{user_id}", json=user_data)
```

### 3. Update operator list to also check org membership

In `list_all_users()`, enhance the tenant_id extraction to check organization membership as fallback:

```python
@router.get("/operator/users", ...)
async def list_all_users(...):
    try:
        users = await list_users(search=search, first=offset, max_results=limit)

        # Optionally pre-fetch org memberships for display
        org_memberships = {}
        try:
            orgs = await get_organizations()
            for org in orgs:
                try:
                    members = await get_organization_members(org["id"])
                    for member in members:
                        org_memberships[member.get("id")] = org.get("name")
                except Exception:
                    pass
        except Exception as e:
            logger.warning(f"Could not fetch organization memberships: {e}")

        formatted = []
        for user in users:
            formatted_user = format_user_response(user)

            # Use org membership as tenant if attribute is missing
            if not formatted_user.get("tenant_id") and user.get("id") in org_memberships:
                formatted_user["tenant_id"] = org_memberships[user["id"]]

            # ... rest of filtering and role fetching
            formatted.append(formatted_user)

        return {"users": formatted, ...}
```

## Verification

1. Create a new user without tenant assignment
2. Assign tenant via operator UI
3. Refresh operator users list - tenant badge should now appear
4. Verify user also appears in tenant's `/users` list
