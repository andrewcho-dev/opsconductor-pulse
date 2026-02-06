# Phase 28.10: Clean Up Tenant Model and Fix InfluxDB Check

## Task 1: Remove Unused Business Model Fields

Remove `plan`, `max_devices`, `max_rules` from the tenant system.

### Database Migration

**Create:** `db/migrations/019_remove_tenant_plan_fields.sql`

```sql
-- Remove unused business model fields (not yet defined)
ALTER TABLE tenants DROP COLUMN IF EXISTS plan;
ALTER TABLE tenants DROP COLUMN IF EXISTS max_devices;
ALTER TABLE tenants DROP COLUMN IF EXISTS max_rules;
```

### Backend Models

**File:** `services/ui_iot/routes/operator.py`

Update `TenantCreate`:
```python
class TenantCreate(BaseModel):
    tenant_id: str  # Must be URL-safe, lowercase
    name: str
    contact_email: Optional[EmailStr] = None
    contact_name: Optional[str] = None
    metadata: dict = {}
```

Update `TenantUpdate`:
```python
class TenantUpdate(BaseModel):
    name: Optional[str] = None
    contact_email: Optional[EmailStr] = None
    contact_name: Optional[str] = None
    status: Optional[str] = None  # ACTIVE, SUSPENDED
    metadata: Optional[dict] = None
```

Update `TenantResponse`:
```python
class TenantResponse(BaseModel):
    tenant_id: str
    name: str
    status: str
    contact_email: Optional[EmailStr]
    contact_name: Optional[str]
    metadata: dict
    created_at: datetime
    updated_at: datetime
```

Update `create_tenant` INSERT statement - remove plan, max_devices, max_rules columns.

Update `update_tenant` - remove those fields from the update loop.

Update SQL queries in `list_tenants` and `get_tenant` - remove those columns from SELECT.

### Frontend - CreateTenantDialog

**File:** `frontend/src/features/operator/CreateTenantDialog.tsx`

Remove plan, maxDevices, maxRules state and form fields if present.

### Frontend - EditTenantDialog

**File:** `frontend/src/features/operator/EditTenantDialog.tsx`

Remove plan, maxDevices, maxRules state and form fields.

### Frontend - API Types

**File:** `frontend/src/services/api/tenants.ts`

Update types to remove plan, max_devices, max_rules fields.

---

## Task 2: Fix InfluxDB Status Check

The tenant detail page shows "InfluxDB Not Found" because:
1. Existing tenants weren't provisioned through the new create flow
2. The query assumes a `telemetry` measurement exists

**File:** `services/ui_iot/routes/operator.py`

Fix `check_tenant_influxdb` to check if database exists without requiring specific data:

```python
async def check_tenant_influxdb(tenant_id: str) -> dict:
    """
    Check if tenant InfluxDB database exists.
    """
    db_name = f"telemetry_{tenant_id}"
    headers = {
        "Authorization": f"Bearer {INFLUXDB_TOKEN}",
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            # Query system tables to check if database exists
            # or try a simple query that works even on empty databases
            resp = await client.post(
                f"{INFLUXDB_URL}/api/v3/query_sql",
                params={"db": db_name, "format": "json"},
                content="SELECT 1 as ping",
                headers=headers,
            )

            if resp.status_code == 200:
                # Database exists, now count telemetry if table exists
                count_resp = await client.post(
                    f"{INFLUXDB_URL}/api/v3/query_sql",
                    params={"db": db_name, "format": "json"},
                    content="SELECT COUNT(*) as count FROM telemetry",
                    headers=headers,
                )
                if count_resp.status_code == 200:
                    data = count_resp.json()
                    count = data[0]["count"] if data else 0
                    return {"exists": True, "telemetry_count": count}
                else:
                    # Database exists but no telemetry table yet
                    return {"exists": True, "telemetry_count": 0}
            elif resp.status_code == 404 or "database" in resp.text.lower():
                return {"exists": False, "telemetry_count": 0}
            else:
                return {"exists": None, "error": resp.text}
    except Exception as exc:
        return {"exists": None, "error": str(exc)}
```

### Provision Existing Tenants

Add an endpoint or script to provision InfluxDB for existing tenants:

```python
@router.post("/tenants/{tenant_id}/provision-influxdb")
async def provision_influxdb(
    request: Request,
    tenant_id: str,
    _: None = Depends(require_operator_admin),
):
    """Manually provision InfluxDB for existing tenant."""
    pool = await get_pool()

    async with operator_connection(pool) as conn:
        exists = await conn.fetchval(
            "SELECT 1 FROM tenants WHERE tenant_id = $1",
            tenant_id,
        )
        if not exists:
            raise HTTPException(404, "Tenant not found")

    success = await provision_tenant_influxdb(tenant_id)

    return {
        "tenant_id": tenant_id,
        "influxdb_provisioned": success,
    }
```

### Add Provision Button to UI

**File:** `frontend/src/features/operator/OperatorTenantDetailPage.tsx`

When InfluxDB shows "Not Found", add a "Provision InfluxDB" button that calls the new endpoint.

---

## Apply Migration

```bash
cd /home/opsconductor/simcloud/compose
docker compose exec iot-postgres psql -U iot -d iotcloud -f /docker-entrypoint-initdb.d/migrations/019_remove_tenant_plan_fields.sql
```

## Rebuild and Test

```bash
cd /home/opsconductor/simcloud/frontend && npm run build
cp -r dist/* ../services/ui_iot/spa/
cd ../compose && docker compose restart ui
```

## Files

| Action | File |
|--------|------|
| CREATE | `db/migrations/019_remove_tenant_plan_fields.sql` |
| MODIFY | `services/ui_iot/routes/operator.py` |
| MODIFY | `frontend/src/features/operator/CreateTenantDialog.tsx` |
| MODIFY | `frontend/src/features/operator/EditTenantDialog.tsx` |
| MODIFY | `frontend/src/features/operator/OperatorTenantDetailPage.tsx` |
| MODIFY | `frontend/src/services/api/tenants.ts` |
