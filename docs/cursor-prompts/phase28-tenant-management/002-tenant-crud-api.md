# Phase 28.2: Tenant CRUD API Endpoints

## Task

Add operator endpoints for tenant CRUD operations.

## Add to operator.py

**File:** `services/ui_iot/routes/operator.py`

### Pydantic Models

```python
from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime

class TenantCreate(BaseModel):
    tenant_id: str  # Must be URL-safe, lowercase
    name: str
    contact_email: Optional[str] = None
    contact_name: Optional[str] = None
    plan: str = "standard"
    max_devices: int = 100
    max_rules: int = 50
    metadata: dict = {}

class TenantUpdate(BaseModel):
    name: Optional[str] = None
    contact_email: Optional[str] = None
    contact_name: Optional[str] = None
    plan: Optional[str] = None
    max_devices: Optional[int] = None
    max_rules: Optional[int] = None
    status: Optional[str] = None  # ACTIVE, SUSPENDED
    metadata: Optional[dict] = None

class TenantResponse(BaseModel):
    tenant_id: str
    name: str
    status: str
    contact_email: Optional[str]
    contact_name: Optional[str]
    plan: str
    max_devices: int
    max_rules: int
    metadata: dict
    created_at: datetime
    updated_at: datetime
```

### Endpoints

```python
@router.get("/tenants")
async def list_tenants(
    request: Request,
    status: str = Query("ACTIVE"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    """List all tenants (operator only)."""
    require_operator(request)
    pool = await get_pool()

    async with operator_connection(pool) as conn:
        rows = await conn.fetch("""
            SELECT tenant_id, name, status, contact_email, contact_name,
                   plan, max_devices, max_rules, metadata, created_at, updated_at
            FROM tenants
            WHERE ($1 = 'ALL' OR status = $1)
            ORDER BY created_at DESC
            LIMIT $2 OFFSET $3
        """, status, limit, offset)

        total = await conn.fetchval("""
            SELECT COUNT(*) FROM tenants WHERE ($1 = 'ALL' OR status = $1)
        """, status)

    await log_operator_access(request, "list_tenants", None)

    return {
        "tenants": [dict(r) for r in rows],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.get("/tenants/{tenant_id}")
async def get_tenant(request: Request, tenant_id: str):
    """Get tenant details (operator only)."""
    require_operator(request)
    pool = await get_pool()

    async with operator_connection(pool) as conn:
        row = await conn.fetchrow("""
            SELECT tenant_id, name, status, contact_email, contact_name,
                   plan, max_devices, max_rules, metadata, created_at, updated_at
            FROM tenants
            WHERE tenant_id = $1
        """, tenant_id)

    if not row:
        raise HTTPException(404, "Tenant not found")

    await log_operator_access(request, "get_tenant", tenant_id)

    return dict(row)


@router.post("/tenants", status_code=201)
async def create_tenant(request: Request, tenant: TenantCreate):
    """Create a new tenant (operator_admin only)."""
    require_operator_admin(request)
    pool = await get_pool()

    # Validate tenant_id format
    import re
    if not re.match(r'^[a-z0-9][a-z0-9\-]{1,62}[a-z0-9]$', tenant.tenant_id):
        raise HTTPException(400, "tenant_id must be lowercase alphanumeric with hyphens, 3-64 chars")

    async with operator_connection(pool) as conn:
        # Check if exists
        exists = await conn.fetchval(
            "SELECT 1 FROM tenants WHERE tenant_id = $1", tenant.tenant_id
        )
        if exists:
            raise HTTPException(409, "Tenant already exists")

        # Create tenant
        await conn.execute("""
            INSERT INTO tenants (tenant_id, name, contact_email, contact_name,
                                 plan, max_devices, max_rules, metadata)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8::jsonb)
        """, tenant.tenant_id, tenant.name, tenant.contact_email, tenant.contact_name,
             tenant.plan, tenant.max_devices, tenant.max_rules, json.dumps(tenant.metadata))

    # Provision InfluxDB database (will be implemented in 004)
    await provision_tenant_influxdb(tenant.tenant_id)

    await log_operator_access(request, "create_tenant", tenant.tenant_id)

    return {"tenant_id": tenant.tenant_id, "status": "created"}


@router.patch("/tenants/{tenant_id}")
async def update_tenant(request: Request, tenant_id: str, update: TenantUpdate):
    """Update tenant (operator_admin only)."""
    require_operator_admin(request)
    pool = await get_pool()

    # Build dynamic update
    updates = []
    params = [tenant_id]
    param_num = 2

    for field in ["name", "contact_email", "contact_name", "plan",
                  "max_devices", "max_rules", "status"]:
        value = getattr(update, field, None)
        if value is not None:
            updates.append(f"{field} = ${param_num}")
            params.append(value)
            param_num += 1

    if update.metadata is not None:
        updates.append(f"metadata = ${param_num}::jsonb")
        params.append(json.dumps(update.metadata))
        param_num += 1

    if not updates:
        raise HTTPException(400, "No fields to update")

    updates.append("updated_at = now()")

    async with operator_connection(pool) as conn:
        result = await conn.execute(f"""
            UPDATE tenants SET {", ".join(updates)}
            WHERE tenant_id = $1 AND status != 'DELETED'
        """, *params)

        if result == "UPDATE 0":
            raise HTTPException(404, "Tenant not found")

    await log_operator_access(request, "update_tenant", tenant_id)

    return {"tenant_id": tenant_id, "status": "updated"}


@router.delete("/tenants/{tenant_id}")
async def delete_tenant(request: Request, tenant_id: str):
    """Soft delete tenant (operator_admin only)."""
    require_operator_admin(request)
    pool = await get_pool()

    async with operator_connection(pool) as conn:
        result = await conn.execute("""
            UPDATE tenants
            SET status = 'DELETED', deleted_at = now(), updated_at = now()
            WHERE tenant_id = $1 AND status != 'DELETED'
        """, tenant_id)

        if result == "UPDATE 0":
            raise HTTPException(404, "Tenant not found or already deleted")

    await log_operator_access(request, "delete_tenant", tenant_id)

    return {"tenant_id": tenant_id, "status": "deleted"}
```

### Helper Functions

```python
def require_operator(request: Request):
    """Require operator or operator_admin role."""
    user = getattr(request.state, "user", None)
    if not user or user.get("role") not in ("operator", "operator_admin"):
        raise HTTPException(403, "Operator access required")

def require_operator_admin(request: Request):
    """Require operator_admin role."""
    user = getattr(request.state, "user", None)
    if not user or user.get("role") != "operator_admin":
        raise HTTPException(403, "Operator admin access required")

async def provision_tenant_influxdb(tenant_id: str):
    """Create InfluxDB database for tenant. Implemented in 004."""
    pass  # Placeholder
```

## Verification

```bash
docker compose restart ui

# Test list tenants (need operator token)
curl -s "http://localhost:8080/operator/tenants" \
  -H "Cookie: pulse_session=<operator_token>"
```

## Files

| Action | File |
|--------|------|
| MODIFY | `services/ui_iot/routes/operator.py` |
