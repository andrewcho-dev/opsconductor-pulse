# Phase 29.2: System Health Aggregation API

## Task

Create `/operator/system/health` endpoint that checks all components and returns unified health status.

---

## Create System Routes File

**File:** `services/ui_iot/routes/system.py`

```python
import os
import time
import logging
from datetime import datetime

import httpx
import asyncpg
from fastapi import APIRouter, Depends, HTTPException
from starlette.requests import Request

from middleware.auth import JWTBearer
from middleware.tenant import inject_tenant_context, require_operator

logger = logging.getLogger(__name__)

# Service URLs (internal Docker network)
POSTGRES_HOST = os.getenv("PG_HOST", "iot-postgres")
POSTGRES_PORT = int(os.getenv("PG_PORT", "5432"))
POSTGRES_DB = os.getenv("PG_DB", "iotcloud")
POSTGRES_USER = os.getenv("PG_USER", "iot")
POSTGRES_PASS = os.getenv("PG_PASS", "iot_dev")

INFLUXDB_URL = os.getenv("INFLUXDB_URL", "http://iot-influxdb:8181")
INFLUXDB_TOKEN = os.getenv("INFLUXDB_TOKEN", "")

KEYCLOAK_INTERNAL_URL = os.getenv("KEYCLOAK_INTERNAL_URL", "http://pulse-keycloak:8080")

INGEST_URL = os.getenv("INGEST_HEALTH_URL", "http://iot-ingest:8080")
EVALUATOR_URL = os.getenv("EVALUATOR_HEALTH_URL", "http://iot-evaluator:8080")
DISPATCHER_URL = os.getenv("DISPATCHER_HEALTH_URL", "http://iot-dispatcher:8080")
DELIVERY_URL = os.getenv("DELIVERY_HEALTH_URL", "http://iot-delivery-worker:8080")

router = APIRouter(
    prefix="/operator/system",
    tags=["system"],
    dependencies=[
        Depends(JWTBearer()),
        Depends(inject_tenant_context),
        Depends(require_operator),
    ],
)


async def check_postgres() -> dict:
    """Check PostgreSQL health."""
    start = time.time()
    try:
        conn = await asyncpg.connect(
            host=POSTGRES_HOST,
            port=POSTGRES_PORT,
            database=POSTGRES_DB,
            user=POSTGRES_USER,
            password=POSTGRES_PASS,
            timeout=5,
        )

        # Get connection count
        connections = await conn.fetchval(
            "SELECT count(*) FROM pg_stat_activity WHERE datname = $1",
            POSTGRES_DB,
        )

        # Get max connections
        max_conn = await conn.fetchval("SHOW max_connections")

        await conn.close()
        latency = int((time.time() - start) * 1000)

        return {
            "status": "healthy",
            "latency_ms": latency,
            "connections": connections,
            "max_connections": int(max_conn),
        }
    except Exception as e:
        logger.error("Postgres health check failed: %s", e)
        return {"status": "down", "error": str(e)}


async def check_influxdb() -> dict:
    """Check InfluxDB health."""
    start = time.time()
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(
                f"{INFLUXDB_URL}/health",
                headers={"Authorization": f"Bearer {INFLUXDB_TOKEN}"},
            )
            latency = int((time.time() - start) * 1000)

            if resp.status_code == 200:
                return {
                    "status": "healthy",
                    "latency_ms": latency,
                }
            return {
                "status": "degraded",
                "latency_ms": latency,
                "http_status": resp.status_code,
            }
    except Exception as e:
        logger.error("InfluxDB health check failed: %s", e)
        return {"status": "down", "error": str(e)}


async def check_keycloak() -> dict:
    """Check Keycloak health."""
    start = time.time()
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{KEYCLOAK_INTERNAL_URL}/health/ready")
            latency = int((time.time() - start) * 1000)

            if resp.status_code == 200:
                return {"status": "healthy", "latency_ms": latency}
            return {
                "status": "degraded",
                "latency_ms": latency,
                "http_status": resp.status_code,
            }
    except Exception as e:
        logger.error("Keycloak health check failed: %s", e)
        return {"status": "down", "error": str(e)}


async def check_service(name: str, url: str) -> dict:
    """Check a service health endpoint."""
    start = time.time()
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{url}/health")
            latency = int((time.time() - start) * 1000)

            if resp.status_code == 200:
                data = resp.json()
                return {
                    "status": "healthy",
                    "latency_ms": latency,
                    "counters": data.get("counters", {}),
                }
            return {
                "status": "degraded",
                "latency_ms": latency,
                "http_status": resp.status_code,
            }
    except httpx.ConnectError:
        return {"status": "down", "error": "Connection refused"}
    except Exception as e:
        logger.error("%s health check failed: %s", name, e)
        return {"status": "unknown", "error": str(e)}


async def check_mqtt() -> dict:
    """Check MQTT broker availability."""
    # Simple TCP connection check
    import socket

    mqtt_host = os.getenv("MQTT_HOST", "iot-mqtt")
    mqtt_port = int(os.getenv("MQTT_PORT", "1883"))

    start = time.time()
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        result = sock.connect_ex((mqtt_host, mqtt_port))
        sock.close()
        latency = int((time.time() - start) * 1000)

        if result == 0:
            return {"status": "healthy", "latency_ms": latency}
        return {"status": "down", "error": f"Connection failed: {result}"}
    except Exception as e:
        return {"status": "down", "error": str(e)}


@router.get("/health")
async def get_system_health(request: Request):
    """
    Get health status of all system components.
    Checks are performed in parallel for speed.
    """
    import asyncio

    # Run all checks in parallel
    results = await asyncio.gather(
        check_postgres(),
        check_influxdb(),
        check_mqtt(),
        check_keycloak(),
        check_service("ingest", INGEST_URL),
        check_service("evaluator", EVALUATOR_URL),
        check_service("dispatcher", DISPATCHER_URL),
        check_service("delivery", DELIVERY_URL),
        return_exceptions=True,
    )

    component_names = [
        "postgres", "influxdb", "mqtt", "keycloak",
        "ingest", "evaluator", "dispatcher", "delivery",
    ]

    components = {}
    for name, result in zip(component_names, results):
        if isinstance(result, Exception):
            components[name] = {"status": "unknown", "error": str(result)}
        else:
            components[name] = result

    # Determine overall status
    statuses = [c.get("status", "unknown") for c in components.values()]
    if all(s == "healthy" for s in statuses):
        overall = "healthy"
    elif any(s == "down" for s in statuses):
        overall = "degraded"
    else:
        overall = "degraded"

    return {
        "status": overall,
        "components": components,
        "checked_at": datetime.utcnow().isoformat() + "Z",
    }
```

---

## Register Router

**File:** `services/ui_iot/app.py`

Add import and include router:

```python
from routes.system import router as system_router

# In create_app() or wherever routers are registered:
app.include_router(system_router)
```

---

## Add Environment Variables

**File:** `compose/docker-compose.yml`

Add to `ui` service environment:

```yaml
  ui:
    environment:
      # ... existing vars ...
      MQTT_HOST: iot-mqtt
      MQTT_PORT: "1883"
      INGEST_HEALTH_URL: "http://iot-ingest:8080"
      EVALUATOR_HEALTH_URL: "http://iot-evaluator:8080"
      DISPATCHER_HEALTH_URL: "http://iot-dispatcher:8080"
      DELIVERY_HEALTH_URL: "http://iot-delivery-worker:8080"
```

---

## Verification

```bash
# Rebuild and restart
cd /home/opsconductor/simcloud/compose
docker compose restart ui

# Test endpoint (as operator)
curl -H "Authorization: Bearer <token>" http://localhost:8080/operator/system/health
```

Expected response:
```json
{
  "status": "healthy",
  "components": {
    "postgres": {"status": "healthy", "latency_ms": 2, "connections": 15, "max_connections": 100},
    "influxdb": {"status": "healthy", "latency_ms": 5},
    "mqtt": {"status": "healthy", "latency_ms": 1},
    "keycloak": {"status": "healthy", "latency_ms": 12},
    "ingest": {"status": "healthy", "latency_ms": 3, "counters": {...}},
    "evaluator": {"status": "healthy", "latency_ms": 2, "counters": {...}},
    "dispatcher": {"status": "healthy", "latency_ms": 2, "counters": {...}},
    "delivery": {"status": "healthy", "latency_ms": 2, "counters": {...}}
  },
  "checked_at": "2024-01-15T10:00:00Z"
}
```

---

## Files

| Action | File |
|--------|------|
| CREATE | `services/ui_iot/routes/system.py` |
| MODIFY | `services/ui_iot/app.py` |
| MODIFY | `compose/docker-compose.yml` |
