# Debug and Fix Tenant Badge Display

## Step 1: Add Debug Logging

In `services/ui_iot/routes/users.py`, add detailed logging to the `list_all_users()` function to diagnose the issue:

```python
@router.get(
    "/operator/users",
    dependencies=[Depends(JWTBearer()), Depends(require_operator)]
)
async def list_all_users(
    search: Optional[str] = Query(None),
    tenant_filter: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0)
):
    """List all users across all tenants."""
    try:
        users = await list_users(search=search, first=offset, max_results=limit)
        logger.info(f"Fetched {len(users)} users from Keycloak")

        # Build org membership lookup
        org_memberships = {}
        try:
            orgs = await get_organizations()
            logger.info(f"Found {len(orgs)} organizations: {[o.get('name') for o in orgs]}")

            for org in orgs:
                org_id = org.get("id")
                org_name = org.get("name")
                try:
                    members = await get_organization_members(org_id)
                    logger.info(f"Org '{org_name}' ({org_id}) has {len(members)} members")

                    for member in members:
                        # Log member structure to understand format
                        member_id = member.get("id")
                        logger.debug(f"  Member: id={member_id}, keys={list(member.keys())}")
                        if member_id:
                            org_memberships[member_id] = org_name
                except Exception as e:
                    logger.warning(f"Failed to get members for org {org_name}: {e}")

            logger.info(f"Built org_memberships with {len(org_memberships)} entries")
            logger.debug(f"org_memberships keys: {list(org_memberships.keys())[:5]}...")

        except Exception as e:
            logger.warning(f"Could not fetch organizations: {e}")

        formatted = []
        for user in users:
            user_id = user.get("id")
            formatted_user = format_user_response(user)
            attr_tenant = formatted_user.get("tenant_id")

            # Log matching attempt
            org_tenant = org_memberships.get(user_id)
            logger.debug(f"User {user.get('username')}: id={user_id}, attr_tenant={attr_tenant}, org_tenant={org_tenant}")

            # Use org membership as fallback
            if not attr_tenant and org_tenant:
                formatted_user["tenant_id"] = org_tenant
                logger.info(f"Applied org fallback for {user.get('username')}: {org_tenant}")

            # ... rest of filtering logic
```

## Step 2: Check Keycloak Org Member Response Format

The Keycloak Organizations API may return members in a different format. Check the actual response:

```python
async def get_organization_members(org_id: str) -> list[dict]:
    """Get members of an organization."""
    members = await _admin_request("GET", f"/organizations/{org_id}/members")
    # Log full response to understand structure
    logger.debug(f"Org {org_id} members raw response: {members}")
    return members or []
```

**Known issue:** Keycloak 26 org members endpoint may return user representations with different ID fields. Check if it's:
- `id` - Standard user ID
- `userId` - Alternative field
- `sub` - Subject claim

## Step 3: Fix ID Matching

If the member response uses a different key, update the lookup:

```python
for member in members:
    # Try multiple possible ID fields
    member_id = (
        member.get("id") or
        member.get("userId") or
        member.get("sub")
    )
    if member_id:
        org_memberships[member_id] = org_name
```

## Step 4: Verify Org Names Match Tenant IDs

Check if organization names in Keycloak match the tenant_id values used elsewhere:

```python
logger.info(f"Org names: {[o.get('name') for o in orgs]}")
logger.info(f"User tenant_id attrs: {[u.get('attributes', {}).get('tenant_id') for u in users[:5]]}")
```

If there's a format mismatch (e.g., org name is "Acme Corp" but tenant_id is "acme-corp"), add normalization:

```python
# Normalize org name to match tenant_id format
org_name_normalized = org.get("name", "").lower().replace(" ", "-")
org_memberships[member_id] = org_name_normalized
```

## Step 5: Alternative - Query Org Membership Per User

If the batch approach doesn't work reliably, query membership per user (slower but more reliable):

```python
async def get_user_organizations(user_id: str) -> list[str]:
    """Get organizations a user belongs to."""
    try:
        # Keycloak 26 user orgs endpoint
        orgs = await _admin_request("GET", f"/users/{user_id}/organizations")
        return [org.get("name") for org in (orgs or [])]
    except Exception:
        return []
```

Then in the list:

```python
for user in users:
    formatted_user = format_user_response(user)

    if not formatted_user.get("tenant_id"):
        # Query user's orgs directly
        user_orgs = await get_user_organizations(user["id"])
        if user_orgs:
            formatted_user["tenant_id"] = user_orgs[0]
```

## Verification

1. Run with debug logging enabled
2. Check logs for:
   - Org fetch success/failure
   - Member ID format
   - Matching attempts and results
3. Identify the specific failure point
4. Apply targeted fix
5. Verify tenant badge appears after assignment

## Expected Log Output (Working)

```
INFO: Fetched 10 users from Keycloak
INFO: Found 2 organizations: ['tenant-a', 'tenant-b']
INFO: Org 'tenant-a' (uuid-123) has 3 members
INFO: Org 'tenant-b' (uuid-456) has 2 members
INFO: Built org_memberships with 5 entries
DEBUG: User customer1: id=abc-123, attr_tenant=tenant-a, org_tenant=tenant-a
DEBUG: User newuser: id=def-456, attr_tenant=None, org_tenant=tenant-a
INFO: Applied org fallback for newuser: tenant-a
```
