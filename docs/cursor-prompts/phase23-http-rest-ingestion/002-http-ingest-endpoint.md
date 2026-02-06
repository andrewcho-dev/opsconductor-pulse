# Phase 23.2: HTTP Single-Message Ingest Endpoint

## Task

Add `POST /ingest/v1/tenant/{tenant_id}/device/{device_id}/{msg_type}` endpoint to `ui_iot` service.

## Step 1: Create the ingest router

Create new file `services/ui_iot/routes/ingest.py`:

```python
import sys
sys.path.insert(0, "/app")

from fastapi import APIRouter, Header, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from shared.ingest_core import validate_and_prepare, IngestResult, sha256_hex

router = APIRouter(prefix="/ingest/v1", tags=["ingest"])

class IngestPayload(BaseModel):
    ts: str | None = None
    site_id: str
    seq: int = 0
    metrics: dict[str, float | int | bool] = {}

@router.post("/tenant/{tenant_id}/device/{device_id}/{msg_type}")
async def ingest_single(
    request: Request,
    tenant_id: str,
    device_id: str,
    msg_type: str,
    payload: IngestPayload,
    x_provision_token: str = Header(..., alias="X-Provision-Token"),
):
    """
    Ingest a single telemetry or heartbeat message via HTTP.

    Returns:
        202 Accepted on success
        400 Bad Request for invalid msg_type
        401 Unauthorized for invalid token
        403 Forbidden for revoked device
        429 Too Many Requests for rate limiting
    """
    if msg_type not in ("telemetry", "heartbeat"):
        raise HTTPException(status_code=400, detail="Invalid msg_type. Must be 'telemetry' or 'heartbeat'")

    # Get shared state
    pool = await request.app.state.get_pool()
    auth_cache = request.app.state.auth_cache
    batch_writer = request.app.state.batch_writer
    rate_buckets = request.app.state.rate_buckets

    # Build payload dict
    payload_dict = {
        "ts": payload.ts,
        "site_id": payload.site_id,
        "seq": payload.seq,
        "metrics": payload.metrics,
    }

    result = await validate_and_prepare(
        pool=pool,
        auth_cache=auth_cache,
        rate_buckets=rate_buckets,
        tenant_id=tenant_id,
        device_id=device_id,
        site_id=payload.site_id,
        msg_type=msg_type,
        provision_token=x_provision_token,
        payload=payload_dict,
        max_payload_bytes=request.app.state.max_payload_bytes,
        rps=request.app.state.rps,
        burst=request.app.state.burst,
        require_token=request.app.state.require_token,
    )

    if not result.success:
        # Map reason to HTTP status
        status_map = {
            "RATE_LIMITED": 429,
            "TOKEN_INVALID": 401,
            "TOKEN_MISSING": 401,
            "TOKEN_NOT_SET_IN_REGISTRY": 401,
            "DEVICE_REVOKED": 403,
            "UNREGISTERED_DEVICE": 403,
            "PAYLOAD_TOO_LARGE": 400,
            "SITE_MISMATCH": 400,
        }
        status = status_map.get(result.reason, 400)
        raise HTTPException(status_code=status, detail=result.reason)

    # Write to InfluxDB
    await batch_writer.add(tenant_id, result.line_protocol)

    return JSONResponse(
        status_code=202,
        content={"status": "accepted", "device_id": device_id, "seq": payload.seq}
    )
```

## Step 2: Modify app.py

Modify `services/ui_iot/app.py`:

**Add imports at top:**
```python
import sys
sys.path.insert(0, "/app")
import httpx
from routes.ingest import router as ingest_router
from shared.ingest_core import DeviceAuthCache, InfluxBatchWriter
```

**Add environment variables after existing ones:**
```python
INFLUXDB_URL = os.getenv("INFLUXDB_URL", "http://iot-influxdb:8181")
INFLUXDB_TOKEN = os.getenv("INFLUXDB_TOKEN", "influx-dev-token-change-me")
AUTH_CACHE_TTL = int(os.getenv("AUTH_CACHE_TTL_SECONDS", "60"))
INFLUX_BATCH_SIZE = int(os.getenv("INFLUX_BATCH_SIZE", "500"))
INFLUX_FLUSH_INTERVAL_MS = int(os.getenv("INFLUX_FLUSH_INTERVAL_MS", "1000"))
REQUIRE_TOKEN = os.getenv("REQUIRE_TOKEN", "1") == "1"
```

**Add router after existing routers:**
```python
app.include_router(ingest_router)
```

**Modify startup() to initialize ingest state:**
```python
@app.on_event("startup")
async def startup():
    await get_pool()

    # Initialize HTTP ingest infrastructure
    app.state.get_pool = get_pool
    app.state.http_client = httpx.AsyncClient(timeout=10.0)
    app.state.auth_cache = DeviceAuthCache(ttl_seconds=AUTH_CACHE_TTL)
    app.state.batch_writer = InfluxBatchWriter(
        app.state.http_client, INFLUXDB_URL, INFLUXDB_TOKEN,
        INFLUX_BATCH_SIZE, INFLUX_FLUSH_INTERVAL_MS
    )
    await app.state.batch_writer.start()
    app.state.rate_buckets = {}
    app.state.max_payload_bytes = 8192
    app.state.rps = 5.0
    app.state.burst = 20.0
    app.state.require_token = REQUIRE_TOKEN

    # existing OAuth logging...
```

**Add shutdown handler:**
```python
@app.on_event("shutdown")
async def shutdown():
    if hasattr(app.state, 'batch_writer'):
        await app.state.batch_writer.stop()
    if hasattr(app.state, 'http_client'):
        await app.state.http_client.aclose()
```

## Verification

```bash
# Syntax check
cd /home/opsconductor/simcloud/services/ui_iot && python3 -c "from routes.ingest import router; print('OK')"
```

## Files

| Action | File |
|--------|------|
| CREATE | `services/ui_iot/routes/ingest.py` |
| MODIFY | `services/ui_iot/app.py` |
