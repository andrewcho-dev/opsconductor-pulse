# Phase 28.4: Tenant InfluxDB Provisioning

## Task

Auto-create InfluxDB database when a tenant is created.

## Add Provisioning Function

**File:** `services/ui_iot/routes/operator.py`

Add at top with imports:
```python
import httpx
import os

INFLUXDB_URL = os.getenv("INFLUXDB_URL", "http://iot-influxdb:8181")
INFLUXDB_TOKEN = os.getenv("INFLUXDB_TOKEN", "influx-dev-token-change-me")
```

Add provisioning function:
```python
async def provision_tenant_influxdb(tenant_id: str) -> bool:
    """
    Create InfluxDB database for tenant.

    InfluxDB 3 auto-creates databases on first write,
    so we write a dummy point to ensure it exists.
    """
    db_name = f"telemetry_{tenant_id}"

    # Write a dummy initialization point
    line_protocol = f"_init,tenant={tenant_id} initialized=1i {int(time.time() * 1_000_000_000)}"

    headers = {
        "Authorization": f"Bearer {INFLUXDB_TOKEN}",
        "Content-Type": "text/plain",
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                f"{INFLUXDB_URL}/api/v3/write_lp?db={db_name}",
                content=line_protocol,
                headers=headers,
            )

            if resp.status_code < 300:
                logger.info(f"Created InfluxDB database {db_name} for tenant {tenant_id}")
                return True
            else:
                logger.error(f"Failed to create InfluxDB database {db_name}: {resp.status_code} {resp.text}")
                return False

    except Exception as e:
        logger.error(f"InfluxDB provisioning error for {tenant_id}: {e}")
        return False


async def check_tenant_influxdb(tenant_id: str) -> dict:
    """
    Check if tenant InfluxDB database exists and get basic stats.
    """
    db_name = f"telemetry_{tenant_id}"

    headers = {
        "Authorization": f"Bearer {INFLUXDB_TOKEN}",
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            # Try to query the database
            resp = await client.post(
                f"{INFLUXDB_URL}/api/v3/query_sql",
                params={"db": db_name, "format": "json"},
                content="SELECT COUNT(*) as count FROM telemetry",
                headers=headers,
            )

            if resp.status_code == 200:
                data = resp.json()
                count = data[0]["count"] if data else 0
                return {"exists": True, "telemetry_count": count}
            elif resp.status_code == 404:
                return {"exists": False, "telemetry_count": 0}
            else:
                return {"exists": None, "error": resp.text}

    except Exception as e:
        return {"exists": None, "error": str(e)}
```

## Update create_tenant to use provisioning

In the `create_tenant` endpoint, replace the placeholder:

```python
@router.post("/tenants", status_code=201)
async def create_tenant(request: Request, tenant: TenantCreate):
    """Create a new tenant (operator_admin only)."""
    require_operator_admin(request)
    pool = await get_pool()

    # ... validation and insert ...

    # Provision InfluxDB database
    influx_ok = await provision_tenant_influxdb(tenant.tenant_id)

    await log_operator_access(request, "create_tenant", tenant.tenant_id)

    return {
        "tenant_id": tenant.tenant_id,
        "status": "created",
        "influxdb_provisioned": influx_ok,
    }
```

## Add InfluxDB status to tenant stats

Update `get_tenant_stats` to include InfluxDB info:

```python
@router.get("/tenants/{tenant_id}/stats")
async def get_tenant_stats(request: Request, tenant_id: str):
    # ... existing code ...

    # Check InfluxDB status
    influx_status = await check_tenant_influxdb(tenant_id)

    return {
        "tenant_id": tenant_id,
        "name": tenant["name"],
        "status": tenant["status"],
        "stats": {
            # ... existing stats ...
        },
        "influxdb": influx_status,
    }
```

## Verification

```bash
docker compose restart ui

# Create a test tenant (as operator_admin)
curl -X POST "http://localhost:8080/operator/tenants" \
  -H "Content-Type: application/json" \
  -H "Cookie: pulse_session=<operator_admin_token>" \
  -d '{"tenant_id": "test-tenant", "name": "Test Tenant"}'

# Verify InfluxDB database was created
docker compose exec iot-influxdb influxdb3 query --database telemetry_test-tenant "SELECT * FROM _init LIMIT 1"
```

## Files

| Action | File |
|--------|------|
| MODIFY | `services/ui_iot/routes/operator.py` |
