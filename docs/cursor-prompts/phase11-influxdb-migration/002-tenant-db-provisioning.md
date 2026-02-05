# Task 002: Tenant Database Provisioning

> **CURSOR: EXECUTE THIS TASK**
>
> Read the instructions below and implement them exactly.
> This task creates a standalone script to provision InfluxDB databases for existing tenants,
> and modifies the provisioning API to auto-create InfluxDB databases for new tenants.
> RUN THE TESTS in the Test section. Do not proceed if tests fail.

---

## Context

InfluxDB 3 Core auto-creates databases on first write. We need:
1. A one-time script to set up databases for existing tenants (reads `device_registry` from PG)
2. A modification to the provisioning API so new tenants get their InfluxDB database created on device creation

The InfluxDB database naming convention is `telemetry_{tenant_id}` — one database per tenant for tenant isolation.

**Read first**:
- `services/provision_api/app.py` (lines 1-30 for env vars, lines 199-239 for `admin_create_device`)
- `services/provision_api/requirements.txt`
- `compose/docker-compose.yml` (the `api` service block — verify INFLUXDB_URL and INFLUXDB_TOKEN are there from Task 001)

---

## Task

### 2.1 Create tenant initialization script

Create `scripts/init_influxdb_tenants.py`:

```python
#!/usr/bin/env python3
"""Initialize InfluxDB databases for all existing tenants.

Reads distinct tenant_id values from device_registry in PostgreSQL,
then writes a dummy point to InfluxDB for each tenant to auto-create
the telemetry_{tenant_id} database.

Usage:
    python scripts/init_influxdb_tenants.py

Environment variables:
    PG_HOST, PG_PORT, PG_DB, PG_USER, PG_PASS - PostgreSQL connection
    INFLUXDB_URL - InfluxDB HTTP URL (default: http://localhost:8181)
    INFLUXDB_TOKEN - InfluxDB auth token
"""
import asyncio
import os
import asyncpg
import httpx


PG_HOST = os.getenv("PG_HOST", "localhost")
PG_PORT = int(os.getenv("PG_PORT", "5432"))
PG_DB = os.getenv("PG_DB", "iotcloud")
PG_USER = os.getenv("PG_USER", "iot")
PG_PASS = os.getenv("PG_PASS", "iot_dev")

INFLUXDB_URL = os.getenv("INFLUXDB_URL", "http://localhost:8181")
INFLUXDB_TOKEN = os.getenv("INFLUXDB_TOKEN", "influx-dev-token-change-me")


async def main():
    conn = await asyncpg.connect(
        host=PG_HOST, port=PG_PORT, database=PG_DB,
        user=PG_USER, password=PG_PASS,
    )

    rows = await conn.fetch("SELECT DISTINCT tenant_id FROM device_registry")
    await conn.close()

    if not rows:
        print("No tenants found in device_registry")
        return

    async with httpx.AsyncClient(timeout=10.0) as client:
        for row in rows:
            tenant_id = row["tenant_id"]
            db_name = f"telemetry_{tenant_id}"

            # Write a dummy init point to auto-create the database
            # This point uses a special _init measurement that won't interfere with real data
            line = f"_init,source=provisioning value=1i"

            try:
                resp = await client.post(
                    f"{INFLUXDB_URL}/api/v3/write_lp?db={db_name}",
                    content=line,
                    headers={
                        "Authorization": f"Bearer {INFLUXDB_TOKEN}",
                        "Content-Type": "text/plain",
                    },
                )
                if resp.status_code < 300:
                    print(f"  OK  telemetry_{tenant_id}")
                else:
                    print(f"  WARN telemetry_{tenant_id}: HTTP {resp.status_code} {resp.text}")
            except Exception as e:
                print(f"  ERR  telemetry_{tenant_id}: {e}")

    print("Done.")


if __name__ == "__main__":
    asyncio.run(main())
```

Make the script executable: `chmod +x scripts/init_influxdb_tenants.py`

### 2.2 Add httpx to provision_api requirements

In `services/provision_api/requirements.txt`, add:

```
httpx==0.27.0
```

### 2.3 Modify provision_api to auto-create InfluxDB databases

In `services/provision_api/app.py`:

**At module level** (after line 19, after `ACTIVATION_TTL_MINUTES`):
```python
INFLUXDB_URL = os.getenv("INFLUXDB_URL", "http://iot-influxdb:8181")
INFLUXDB_TOKEN = os.getenv("INFLUXDB_TOKEN", "influx-dev-token-change-me")

_influx_tenants: set[str] = set()
```

**Add import** at the top (after `import asyncpg`):
```python
import httpx
import logging

logger = logging.getLogger(__name__)
```

**Add helper function** (before `admin_create_device` at line 199):
```python
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
                logger.warning("InfluxDB DB create failed for %s: %s %s", db_name, resp.status_code, resp.text)
    except Exception:
        logger.warning("InfluxDB DB create failed for %s", db_name, exc_info=True)
```

**Modify `admin_create_device`** (after the PG inserts, before the return statement — around line 232):

Add this block after the `conn.execute` for `device_activation`:
```python
    # Best-effort: ensure InfluxDB database exists for this tenant
    try:
        await _ensure_influx_db(payload.tenant_id)
    except Exception:
        logger.warning("Failed to ensure InfluxDB DB for tenant %s", payload.tenant_id)
```

---

## Files to Create/Modify

| Action | Path |
|--------|------|
| CREATE | `scripts/init_influxdb_tenants.py` |
| MODIFY | `services/provision_api/app.py` |
| MODIFY | `services/provision_api/requirements.txt` |

---

## Test

```bash
# 1. Ensure the stack is running (InfluxDB + PG)
cd compose && docker compose up -d

# 2. Run the init script (needs PG accessible from host)
cd /home/opsconductor/simcloud
PG_HOST=localhost INFLUXDB_URL=http://localhost:8181 python scripts/init_influxdb_tenants.py
# Should print: OK  telemetry_enabled

# 3. Verify the database was created by querying it
curl -s -X POST http://localhost:8181/api/v3/query_sql \
  -H "Authorization: Bearer influx-dev-token-change-me" \
  -H "Content-Type: application/json" \
  -d '{"db":"telemetry_enabled","q":"SELECT * FROM _init LIMIT 1"}'
# Should return data (not an error)

# 4. Rebuild the api service
cd compose && docker compose up -d --build api

# 5. Run existing unit tests
cd /home/opsconductor/simcloud
python -m pytest tests/unit/ -v -x
```

---

## Acceptance Criteria

- [ ] `scripts/init_influxdb_tenants.py` exists and is executable
- [ ] Running the script creates `telemetry_enabled` database in InfluxDB
- [ ] `services/provision_api/app.py` has `_ensure_influx_db()` helper
- [ ] `admin_create_device` calls `_ensure_influx_db()` after PG inserts
- [ ] InfluxDB failures in provisioning are logged but do not block device creation
- [ ] `httpx==0.27.0` is in `services/provision_api/requirements.txt`
- [ ] All existing unit tests still pass

---

## Commit

```
Add InfluxDB tenant database provisioning

- Create init_influxdb_tenants.py script for existing tenants
- Modify provision API to auto-create InfluxDB DB on device creation
- Add httpx to provision_api dependencies
- Uses auto-creation via dummy write (InfluxDB 3 Core)

Part of Phase 11: InfluxDB Telemetry Migration
```
