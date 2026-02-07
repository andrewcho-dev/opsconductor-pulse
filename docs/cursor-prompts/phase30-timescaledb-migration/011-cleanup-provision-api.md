# Phase 30.11: Remove InfluxDB from Provision API

## Task

Remove InfluxDB provisioning code from `services/provision_api/app.py`. With TimescaleDB, all tenants share the same `telemetry` table (isolated by `tenant_id` column), so per-tenant database creation is no longer needed.

---

## Changes Required

### 1. Remove InfluxDB Configuration

**Delete lines 24-27:**
```python
# DELETE:
INFLUXDB_URL = os.getenv("INFLUXDB_URL", "http://iot-influxdb:8181")
INFLUXDB_TOKEN = os.getenv("INFLUXDB_TOKEN", "influx-dev-token-change-me")

_influx_tenants: set[str] = set()
```

### 2. Remove httpx Import

**Remove from imports (line 9):**
```python
# DELETE:
import httpx
```

### 3. Delete _ensure_influx_db Function

**Delete the entire function (lines 207-233):**
```python
# DELETE ENTIRE FUNCTION:
async def _ensure_influx_db(tenant_id: str) -> None:
    """Best-effort: write a dummy point to auto-create the InfluxDB database."""
    if tenant_id in _influx_tenants:
        return
    db_name = f"telemetry_{tenant_id}"
    line = "_init,source=provisioning value=1i"
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                f"{INFLUXDB_URL}/api/v3/write_lp?db={db_name}",
                content=line,
                headers={
                    "Authorization": f"Bearer {INFLUXDB_TOKEN}",
                    "Content-Type": "text/plain",
                },
            )
            if resp.status_code < 300:
                _influx_tenants.add(tenant_id)
            else:
                logger.warning(
                    "InfluxDB DB create failed for %s: %s %s",
                    db_name,
                    resp.status_code,
                    resp.text,
                )
    except Exception:
        logger.warning("InfluxDB DB create failed for %s", db_name, exc_info=True)
```

### 4. Remove InfluxDB Call from admin_create_device

**In `admin_create_device()` function, delete lines 270-274:**
```python
# DELETE:
    # Best-effort: ensure InfluxDB database exists for this tenant
    try:
        await _ensure_influx_db(payload.tenant_id)
    except Exception:
        logger.warning("Failed to ensure InfluxDB DB for tenant %s", payload.tenant_id)
```

---

## After Changes

The `admin_create_device` function should end simply with:
```python
        # insert activation record (multiple codes over time allowed)
        await conn.execute(
            """
            INSERT INTO device_activation (tenant_id, device_id, activation_code_hash, site_id, expires_at)
            VALUES ($1,$2,$3,$4,$5)
            """,
            payload.tenant_id, payload.device_id, activation_hash, payload.site_id, expires_at
        )

    return AdminCreateDeviceResponse(
        tenant_id=payload.tenant_id,
        device_id=payload.device_id,
        site_id=payload.site_id,
        activation_code=activation_code,
        expires_at=expires_at.isoformat()
    )
```

---

## Verification

```bash
# Restart provision_api
cd /home/opsconductor/simcloud/compose
docker compose restart iot-api

# Check for any import errors
docker compose logs iot-api --tail=20

# Test device provisioning still works
curl -X POST http://localhost:8081/api/admin/devices \
  -H "X-Admin-Key: change-me-now" \
  -H "Content-Type: application/json" \
  -d '{"tenant_id": "test-tenant", "device_id": "test-dev-001", "site_id": "test-site"}'

# Verify device was created
docker compose exec postgres psql -U iot -d iotcloud -c "
SELECT tenant_id, device_id, status FROM device_registry WHERE device_id = 'test-dev-001';
"
```

---

## Files

| Action | File |
|--------|------|
| MODIFY | `services/provision_api/app.py` |
