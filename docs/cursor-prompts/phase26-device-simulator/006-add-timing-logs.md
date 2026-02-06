# Phase 26.6: Add Timing Logs to Find Bottleneck

## Problem

- InfluxDB CLI query: 0.7s
- HTTP to InfluxDB: 0.02s
- But API endpoint takes 1-2 minutes

Something else in the API code is slow.

## Add Timing Logs

**File:** `services/ui_iot/routes/api_v2.py`

Find the telemetry endpoint and add timing around each step:

```python
import time
import logging

logger = logging.getLogger(__name__)

@router.get("/devices/{device_id}/telemetry")
async def get_device_telemetry(
    device_id: str,
    request: Request,
    limit: int = Query(500),
    start: str | None = Query(None),
    end: str | None = Query(None),
):
    t0 = time.time()
    logger.info(f"[timing] START telemetry request device={device_id}")

    # Validation
    t1 = time.time()
    # ... validation code ...
    logger.info(f"[timing] validation done: {time.time() - t1:.2f}s")

    # Get tenant
    t2 = time.time()
    tenant_id = request.state.tenant_id
    logger.info(f"[timing] tenant_id={tenant_id}: {time.time() - t2:.2f}s")

    # Fetch device (verify exists)
    t3 = time.time()
    device = await fetch_device_v2(pool, tenant_id, device_id)
    logger.info(f"[timing] fetch_device_v2: {time.time() - t3:.2f}s")

    if not device:
        raise HTTPException(404, "Device not found")

    # Fetch telemetry from InfluxDB
    t4 = time.time()
    data = await fetch_device_telemetry_dynamic(http_client, tenant_id, device_id, start, end, limit)
    logger.info(f"[timing] fetch_telemetry: {time.time() - t4:.2f}s")

    # Build response
    t5 = time.time()
    response = {"tenant_id": tenant_id, "device_id": device_id, "telemetry": data, "count": len(data)}
    logger.info(f"[timing] build_response: {time.time() - t5:.2f}s")

    logger.info(f"[timing] TOTAL: {time.time() - t0:.2f}s")
    return JSONResponse(jsonable_encoder(response))
```

**Also in** `services/ui_iot/db/influx_queries.py`:

```python
async def fetch_device_telemetry_dynamic(...):
    t0 = time.time()

    # Build SQL
    t1 = time.time()
    # ... SQL construction ...
    logger.info(f"[timing][influx] SQL built: {time.time() - t1:.2f}s")

    # Execute HTTP request
    t2 = time.time()
    resp = await http_client.post(...)
    logger.info(f"[timing][influx] HTTP done: {time.time() - t2:.2f}s status={resp.status_code}")

    # Parse response
    t3 = time.time()
    rows = resp.json()
    logger.info(f"[timing][influx] JSON parsed: {time.time() - t3:.2f}s rows={len(rows)}")

    # Extract metrics
    t4 = time.time()
    result = [extract_metrics(row) for row in rows]
    logger.info(f"[timing][influx] metrics extracted: {time.time() - t4:.2f}s")

    logger.info(f"[timing][influx] TOTAL: {time.time() - t0:.2f}s")
    return result
```

## Restart and Test

```bash
docker compose restart ui
```

Load device detail page, then check logs:

```bash
docker compose logs ui --tail=200 | grep timing
```

Report which step is slow.

## Files

| File | Action |
|------|--------|
| `services/ui_iot/routes/api_v2.py` | Add timing logs |
| `services/ui_iot/db/influx_queries.py` | Add timing logs |
