# Phase 28.8: Debug Create Tenant 400 Error

## Problem

Creating a new tenant returns `API error: 400`.

## Step 1: Check browser DevTools

Open Network tab, try creating tenant again, look at the actual response body. It should say why it failed (e.g., "tenant_id must be lowercase", "Tenant already exists").

## Step 2: Add error details to frontend

**File:** `frontend/src/features/operator/CreateTenantDialog.tsx`

Improve error handling to show the actual API message:

```typescript
{mutation.isError && (
  <p className="text-sm text-destructive">
    {mutation.error instanceof Error
      ? mutation.error.message
      : "Failed to create tenant"}
  </p>
)}
```

Also check if axios is returning the detail:
```typescript
const mutation = useMutation({
  mutationFn: createTenant,
  onError: (error: any) => {
    console.error("Create tenant error:", error.response?.data);
  },
  // ...
});
```

## Step 3: Check API validation

**File:** `services/ui_iot/routes/operator.py`

Find `create_tenant` endpoint and check:

1. Is `require_operator_admin` being called? You need to be logged in as `operator_admin`, not just `operator`.

2. Tenant ID validation regex:
```python
if not re.match(r'^[a-z0-9][a-z0-9\-]{1,62}[a-z0-9]$', tenant.tenant_id):
    raise HTTPException(400, "tenant_id must be lowercase alphanumeric with hyphens, 3-64 chars")
```
This requires:
- Start and end with letter or number
- Middle can have hyphens
- 3-64 characters total

3. Check if tenant already exists:
```python
exists = await conn.fetchval(
    "SELECT 1 FROM tenants WHERE tenant_id = $1", tenant.tenant_id
)
if exists:
    raise HTTPException(409, "Tenant already exists")
```

## Step 4: Check request payload

Add logging to the endpoint:
```python
@router.post("/tenants", status_code=201)
async def create_tenant(request: Request, tenant: TenantCreate):
    import logging
    logging.info(f"Create tenant request: {tenant}")
    # ...
```

## Common Issues

| Error | Cause |
|-------|-------|
| 400 "tenant_id must be..." | ID doesn't match regex (e.g., uppercase, too short, starts with hyphen) |
| 403 "Operator admin required" | Not logged in as operator_admin |
| 409 "Tenant already exists" | Duplicate tenant_id |
| 400 validation error | Missing required field |

## Quick Test

Try creating with a simple ID like `test-company-1` (all lowercase, no special chars).

If that works, the issue is with the tenant_id format being submitted.

## Fix if needed

If the regex is too strict, relax it:
```python
# More permissive - allows 2+ chars
if not re.match(r'^[a-z0-9][a-z0-9\-]*[a-z0-9]$|^[a-z0-9]{1,2}$', tenant.tenant_id):
```

Or just validate basic rules:
```python
if not tenant.tenant_id or len(tenant.tenant_id) < 2 or len(tenant.tenant_id) > 64:
    raise HTTPException(400, "tenant_id must be 2-64 characters")
if not tenant.tenant_id.replace('-', '').isalnum():
    raise HTTPException(400, "tenant_id must contain only letters, numbers, and hyphens")
if tenant.tenant_id.upper() != tenant.tenant_id.lower() and tenant.tenant_id != tenant.tenant_id.lower():
    raise HTTPException(400, "tenant_id must be lowercase")
```
