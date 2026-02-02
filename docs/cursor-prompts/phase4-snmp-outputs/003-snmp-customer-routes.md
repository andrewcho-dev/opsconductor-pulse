# Task 003: SNMP Customer Routes

> **CURSOR: EXECUTE THIS TASK**
>
> This is an implementation task. Read the instructions below and implement them.
> Modify the files listed in "Files to Create/Modify" section.
> Follow the acceptance criteria to verify your work.
> Commit with the message in the "Commit" section when done.

---

## Context

Customers need API endpoints to manage their SNMP integrations. These follow the same pattern as webhook integrations but with SNMP-specific fields. Must enforce tenant isolation and role-based access.

**Read first**:
- `services/ui_iot/routes/customer.py` (existing customer routes)
- `services/ui_iot/schemas/snmp.py` (SNMP schemas from Task 001)
- `services/ui_iot/routes/customer.py` webhook integration routes

**Depends on**: Tasks 001, 002

## Task

### 3.1 Add SNMP integration routes

Update `services/ui_iot/routes/customer.py` to add SNMP endpoints:

```python
from services.ui_iot.schemas.snmp import (
    SNMPIntegrationCreate,
    SNMPIntegrationUpdate,
    SNMPIntegrationResponse,
)

# ... existing imports ...


# ============================================
# SNMP Integration Routes
# ============================================

@router.get("/integrations/snmp", response_model=list[SNMPIntegrationResponse])
async def list_snmp_integrations(
    request: Request,
    tenant_id: str = Depends(get_tenant_id),
    db = Depends(get_tenant_connection),
):
    """List all SNMP integrations for this tenant."""
    query = """
        SELECT id, tenant_id, name, snmp_host, snmp_port, snmp_config,
               snmp_oid_prefix, enabled, created_at, updated_at
        FROM integrations
        WHERE tenant_id = $1 AND type = 'snmp'
        ORDER BY created_at DESC
    """
    rows = await db.fetch(query, tenant_id)

    return [
        SNMPIntegrationResponse(
            id=row["id"],
            tenant_id=row["tenant_id"],
            name=row["name"],
            snmp_host=row["snmp_host"],
            snmp_port=row["snmp_port"],
            snmp_version=row["snmp_config"].get("version", "2c"),
            snmp_oid_prefix=row["snmp_oid_prefix"],
            enabled=row["enabled"],
            created_at=row["created_at"].isoformat(),
            updated_at=row["updated_at"].isoformat(),
        )
        for row in rows
    ]


@router.get("/integrations/snmp/{integration_id}", response_model=SNMPIntegrationResponse)
async def get_snmp_integration(
    integration_id: str,
    tenant_id: str = Depends(get_tenant_id),
    db = Depends(get_tenant_connection),
):
    """Get a specific SNMP integration."""
    # Validate UUID format
    try:
        uuid.UUID(integration_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Integration not found")

    query = """
        SELECT id, tenant_id, name, snmp_host, snmp_port, snmp_config,
               snmp_oid_prefix, enabled, created_at, updated_at
        FROM integrations
        WHERE id = $1 AND tenant_id = $2 AND type = 'snmp'
    """
    row = await db.fetchrow(query, integration_id, tenant_id)

    if not row:
        raise HTTPException(status_code=404, detail="Integration not found")

    return SNMPIntegrationResponse(
        id=row["id"],
        tenant_id=row["tenant_id"],
        name=row["name"],
        snmp_host=row["snmp_host"],
        snmp_port=row["snmp_port"],
        snmp_version=row["snmp_config"].get("version", "2c"),
        snmp_oid_prefix=row["snmp_oid_prefix"],
        enabled=row["enabled"],
        created_at=row["created_at"].isoformat(),
        updated_at=row["updated_at"].isoformat(),
    )


@router.post("/integrations/snmp", response_model=SNMPIntegrationResponse, status_code=201)
async def create_snmp_integration(
    request: Request,
    data: SNMPIntegrationCreate,
    tenant_id: str = Depends(get_tenant_id),
    role: str = Depends(get_user_role),
    db = Depends(get_tenant_connection),
):
    """Create a new SNMP integration."""
    # Require customer_admin role for writes
    if role not in ("customer_admin",):
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    # Address validation happens in Task 004
    # For now, basic validation only

    integration_id = str(uuid.uuid4())
    now = datetime.utcnow()

    # Convert pydantic model to dict for JSON storage
    snmp_config = data.snmp_config.model_dump()

    query = """
        INSERT INTO integrations (
            id, tenant_id, name, type, snmp_host, snmp_port,
            snmp_config, snmp_oid_prefix, enabled, created_at, updated_at
        )
        VALUES ($1, $2, $3, 'snmp', $4, $5, $6, $7, $8, $9, $10)
        RETURNING id, tenant_id, name, snmp_host, snmp_port, snmp_config,
                  snmp_oid_prefix, enabled, created_at, updated_at
    """
    row = await db.fetchrow(
        query,
        integration_id,
        tenant_id,
        data.name,
        data.snmp_host,
        data.snmp_port,
        json.dumps(snmp_config),
        data.snmp_oid_prefix,
        data.enabled,
        now,
        now,
    )

    return SNMPIntegrationResponse(
        id=row["id"],
        tenant_id=row["tenant_id"],
        name=row["name"],
        snmp_host=row["snmp_host"],
        snmp_port=row["snmp_port"],
        snmp_version=snmp_config.get("version", "2c"),
        snmp_oid_prefix=row["snmp_oid_prefix"],
        enabled=row["enabled"],
        created_at=row["created_at"].isoformat(),
        updated_at=row["updated_at"].isoformat(),
    )


@router.patch("/integrations/snmp/{integration_id}", response_model=SNMPIntegrationResponse)
async def update_snmp_integration(
    integration_id: str,
    data: SNMPIntegrationUpdate,
    tenant_id: str = Depends(get_tenant_id),
    role: str = Depends(get_user_role),
    db = Depends(get_tenant_connection),
):
    """Update an SNMP integration."""
    # Require customer_admin role for writes
    if role not in ("customer_admin",):
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    # Validate UUID format
    try:
        uuid.UUID(integration_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Integration not found")

    # Check integration exists and belongs to tenant
    existing = await db.fetchrow(
        "SELECT id, snmp_config FROM integrations WHERE id = $1 AND tenant_id = $2 AND type = 'snmp'",
        integration_id,
        tenant_id,
    )
    if not existing:
        raise HTTPException(status_code=404, detail="Integration not found")

    # Build update query dynamically
    updates = []
    values = []
    param_idx = 1

    # Check if any fields are being updated
    update_data = data.model_dump(exclude_unset=True)
    if not update_data:
        raise HTTPException(status_code=400, detail="No fields to update")

    if data.name is not None:
        updates.append(f"name = ${param_idx}")
        values.append(data.name)
        param_idx += 1

    if data.snmp_host is not None:
        # Address validation happens in Task 004
        updates.append(f"snmp_host = ${param_idx}")
        values.append(data.snmp_host)
        param_idx += 1

    if data.snmp_port is not None:
        updates.append(f"snmp_port = ${param_idx}")
        values.append(data.snmp_port)
        param_idx += 1

    if data.snmp_config is not None:
        snmp_config = data.snmp_config.model_dump()
        updates.append(f"snmp_config = ${param_idx}")
        values.append(json.dumps(snmp_config))
        param_idx += 1

    if data.snmp_oid_prefix is not None:
        updates.append(f"snmp_oid_prefix = ${param_idx}")
        values.append(data.snmp_oid_prefix)
        param_idx += 1

    if data.enabled is not None:
        updates.append(f"enabled = ${param_idx}")
        values.append(data.enabled)
        param_idx += 1

    # Always update updated_at
    updates.append(f"updated_at = ${param_idx}")
    values.append(datetime.utcnow())
    param_idx += 1

    # Add WHERE clause params
    values.append(integration_id)
    values.append(tenant_id)

    query = f"""
        UPDATE integrations
        SET {", ".join(updates)}
        WHERE id = ${param_idx} AND tenant_id = ${param_idx + 1} AND type = 'snmp'
        RETURNING id, tenant_id, name, snmp_host, snmp_port, snmp_config,
                  snmp_oid_prefix, enabled, created_at, updated_at
    """
    row = await db.fetchrow(query, *values)

    return SNMPIntegrationResponse(
        id=row["id"],
        tenant_id=row["tenant_id"],
        name=row["name"],
        snmp_host=row["snmp_host"],
        snmp_port=row["snmp_port"],
        snmp_version=row["snmp_config"].get("version", "2c"),
        snmp_oid_prefix=row["snmp_oid_prefix"],
        enabled=row["enabled"],
        created_at=row["created_at"].isoformat(),
        updated_at=row["updated_at"].isoformat(),
    )


@router.delete("/integrations/snmp/{integration_id}", status_code=204)
async def delete_snmp_integration(
    integration_id: str,
    tenant_id: str = Depends(get_tenant_id),
    role: str = Depends(get_user_role),
    db = Depends(get_tenant_connection),
):
    """Delete an SNMP integration."""
    # Require customer_admin role for writes
    if role not in ("customer_admin",):
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    # Validate UUID format
    try:
        uuid.UUID(integration_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Integration not found")

    result = await db.execute(
        "DELETE FROM integrations WHERE id = $1 AND tenant_id = $2 AND type = 'snmp'",
        integration_id,
        tenant_id,
    )

    if result == "DELETE 0":
        raise HTTPException(status_code=404, detail="Integration not found")

    return Response(status_code=204)
```

### 3.2 Add combined integrations list endpoint

Add endpoint to list all integrations (webhook + SNMP):

```python
@router.get("/integrations")
async def list_all_integrations(
    request: Request,
    type: Optional[str] = None,  # Filter by type: "webhook" or "snmp"
    tenant_id: str = Depends(get_tenant_id),
    db = Depends(get_tenant_connection),
):
    """List all integrations for this tenant."""
    query = """
        SELECT id, tenant_id, name, type, webhook_url, snmp_host, snmp_port,
               snmp_config, snmp_oid_prefix, enabled, created_at, updated_at
        FROM integrations
        WHERE tenant_id = $1
    """
    params = [tenant_id]

    if type:
        if type not in ("webhook", "snmp"):
            raise HTTPException(status_code=400, detail="Invalid type filter")
        query += " AND type = $2"
        params.append(type)

    query += " ORDER BY created_at DESC"
    rows = await db.fetch(query, *params)

    integrations = []
    for row in rows:
        if row["type"] == "webhook":
            integrations.append({
                "id": row["id"],
                "tenant_id": row["tenant_id"],
                "name": row["name"],
                "type": "webhook",
                "webhook_url": row["webhook_url"],
                "enabled": row["enabled"],
                "created_at": row["created_at"].isoformat(),
                "updated_at": row["updated_at"].isoformat(),
            })
        else:  # snmp
            integrations.append({
                "id": row["id"],
                "tenant_id": row["tenant_id"],
                "name": row["name"],
                "type": "snmp",
                "snmp_host": row["snmp_host"],
                "snmp_port": row["snmp_port"],
                "snmp_version": row["snmp_config"].get("version", "2c") if row["snmp_config"] else None,
                "snmp_oid_prefix": row["snmp_oid_prefix"],
                "enabled": row["enabled"],
                "created_at": row["created_at"].isoformat(),
                "updated_at": row["updated_at"].isoformat(),
            })

    return {"integrations": integrations}
```

### 3.3 Add required imports

Ensure these imports are at the top of `customer.py`:

```python
import uuid
import json
from datetime import datetime
from typing import Optional
from fastapi import Request, Response, HTTPException, Depends
```

## Files to Create/Modify

| Action | Path |
|--------|------|
| MODIFY | `services/ui_iot/routes/customer.py` |

## Acceptance Criteria

- [ ] GET /customer/integrations/snmp lists SNMP integrations
- [ ] GET /customer/integrations/snmp/{id} returns single integration
- [ ] POST /customer/integrations/snmp creates new integration
- [ ] PATCH /customer/integrations/snmp/{id} updates integration
- [ ] DELETE /customer/integrations/snmp/{id} removes integration
- [ ] GET /customer/integrations lists all types with optional filter
- [ ] Tenant isolation enforced on all routes
- [ ] customer_admin role required for writes
- [ ] SNMP credentials not returned in responses

**Test**:
```bash
# Get token
TOKEN=$(curl -s -X POST "http://localhost:8180/realms/pulse/protocol/openid-connect/token" \
  -d "grant_type=password&client_id=pulse-ui&username=customer1&password=test123" | jq -r '.access_token')

# List SNMP integrations
curl -H "Authorization: Bearer $TOKEN" http://localhost:8080/customer/integrations/snmp

# Create SNMP integration
curl -X POST -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name":"Test SNMP","snmp_host":"192.168.1.100","snmp_port":162,"snmp_config":{"version":"2c","community":"public"}}' \
  http://localhost:8080/customer/integrations/snmp

# List all integrations
curl -H "Authorization: Bearer $TOKEN" http://localhost:8080/customer/integrations
```

## Commit

```
Add customer SNMP integration routes

- CRUD endpoints for SNMP integrations
- Combined integrations list with type filter
- Tenant isolation enforced
- customer_admin role required for writes
- SNMP credentials masked in responses

Part of Phase 4: SNMP and Alternative Outputs
```
