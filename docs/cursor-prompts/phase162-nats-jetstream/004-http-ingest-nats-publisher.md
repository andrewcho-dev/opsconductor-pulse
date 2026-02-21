# Task 4: HTTP Ingest → NATS Publisher

## File to Modify

- `services/ui_iot/routes/ingest.py`
- `services/ui_iot/app.py` (NATS connection lifecycle)

## What to Do

Refactor the HTTP ingest endpoints to publish messages to NATS instead of writing directly to the database. This unifies both ingestion paths (MQTT and HTTP) through the same NATS → ingest worker pipeline.

### Step 1: Add NATS connection to the ui_iot service

In `services/ui_iot/app.py`, add NATS connection on startup:

```python
import nats

_nats_client = None

async def get_nats():
    global _nats_client
    if _nats_client is None or not _nats_client.is_connected:
        nats_url = os.getenv("NATS_URL", "nats://localhost:4222")
        _nats_client = await nats.connect(nats_url)
    return _nats_client
```

Add cleanup on shutdown:

```python
@app.on_event("shutdown")
async def shutdown_nats():
    if _nats_client:
        await _nats_client.drain()
```

### Step 2: Refactor the single-message ingest endpoint

In `services/ui_iot/routes/ingest.py`, the `POST /ingest/v1/tenant/{tenant_id}/device/{device_id}/{msg_type}` endpoint currently:
1. Validates the request
2. Checks the provision token
3. Performs device registry lookup
4. Writes directly to telemetry table via SQL INSERT

Change it to:
1. Validate request format (keep — fast, no DB)
2. Quick provision token format check (keep — just check it exists)
3. **Publish to NATS** `telemetry.{tenant_id}` with the payload envelope
4. Return `202 Accepted` immediately

The detailed validation (device registry lookup, rate limiting, sensor discovery) will happen in the ingest worker when it consumes from NATS.

```python
@router.post("/ingest/v1/tenant/{tenant_id}/device/{device_id}/{msg_type}")
async def ingest_single(
    tenant_id: str,
    device_id: str,
    msg_type: str,
    request: Request,
):
    # Quick validation
    token = request.headers.get("X-Provision-Token")
    if not token:
        raise HTTPException(status_code=401, detail="Missing X-Provision-Token")

    if msg_type not in ("telemetry", "heartbeat"):
        raise HTTPException(status_code=400, detail="Invalid msg_type")

    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body")

    # Add provision token to payload for downstream validation
    payload["provision_token"] = token

    # Publish to NATS
    nc = await get_nats()
    topic = f"tenant/{tenant_id}/device/{device_id}/{msg_type}"
    envelope = json.dumps({
        "topic": topic,
        "tenant_id": tenant_id,
        "device_id": device_id,
        "msg_type": msg_type,
        "username": "",  # No MQTT username for HTTP path
        "payload": payload,
        "ts": int(time.time() * 1000),
    }, default=str).encode()

    try:
        await nc.publish(f"telemetry.{tenant_id}", envelope)
    except Exception as e:
        logger.error("nats_publish_error", extra={"error": str(e)})
        raise HTTPException(status_code=503, detail="Ingestion temporarily unavailable")

    return JSONResponse(status_code=202, content={"status": "accepted"})
```

### Step 3: Refactor the batch ingest endpoint

Same pattern — validate format, publish each message to NATS:

```python
@router.post("/ingest/v1/batch")
async def ingest_batch(request: Request):
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    messages = body.get("messages", [])
    if not messages:
        raise HTTPException(status_code=400, detail="No messages")
    if len(messages) > 100:
        raise HTTPException(status_code=400, detail="Max 100 messages per batch")

    nc = await get_nats()
    results = []

    for i, msg in enumerate(messages):
        tenant_id = msg.get("tenant_id")
        device_id = msg.get("device_id")
        msg_type = msg.get("msg_type", "telemetry")
        token = msg.get("provision_token")

        if not tenant_id or not device_id:
            results.append({"index": i, "status": "rejected", "reason": "missing tenant_id or device_id"})
            continue
        if not token:
            results.append({"index": i, "status": "rejected", "reason": "missing provision_token"})
            continue

        topic = f"tenant/{tenant_id}/device/{device_id}/{msg_type}"
        envelope = json.dumps({
            "topic": topic,
            "tenant_id": tenant_id,
            "device_id": device_id,
            "msg_type": msg_type,
            "username": "",
            "payload": msg,
            "ts": int(time.time() * 1000),
        }, default=str).encode()

        try:
            await nc.publish(f"telemetry.{tenant_id}", envelope)
            results.append({"index": i, "status": "accepted"})
        except Exception as e:
            results.append({"index": i, "status": "rejected", "reason": "publish_failed"})

    accepted = sum(1 for r in results if r["status"] == "accepted")
    rejected = sum(1 for r in results if r["status"] == "rejected")

    return {
        "accepted": accepted,
        "rejected": rejected,
        "results": results,
    }
```

### Step 4: Remove direct DB writes from ingest routes

Remove or comment out:
- Direct `INSERT INTO telemetry` statements
- Inline sensor discovery calls
- Inline rate limiting (the ingest worker handles this)
- Device registry lookups (the ingest worker handles this)

**Keep** the rate-limit metrics endpoint (`GET /ingest/v1/metrics/rate-limits`) — it queries the ingest worker's state, which may need to be exposed differently now.

### Step 5: Add nats-py to ui_iot requirements

```
nats-py>=2.7.0
```

### Step 6: Update docker-compose.yml

Add `NATS_URL` to the `ui` service environment (if not already done in Task 1):

```yaml
  ui:
    environment:
      NATS_URL: "nats://iot-nats:4222"
    depends_on:
      nats:
        condition: service_healthy
```

## Important Notes

- **Response semantics change:** The HTTP endpoint now returns `202 Accepted` as soon as the message is published to NATS, **before** validation and DB write. This is a trade-off: faster response, but the client doesn't know if the message will be rejected (e.g., invalid token). This matches the MQTT behavior (broker accepts the publish, ingest validates later).
- **If synchronous validation is required:** Keep a lightweight token check in the HTTP endpoint (hash the token and compare against a cached set). This is optional.
- **Benefits gained:** HTTP ingested data now flows through the same batch writer, sensor discovery, message routing, and rate limiting as MQTT data. All bugs fixed in one pipeline apply to both paths.
- **NATS publish is fast** — typically <1ms to publish to a local NATS instance. The endpoint should respond in <5ms.

## Verification

```bash
# Test single message
curl -s --insecure -X POST \
  -H "Content-Type: application/json" \
  -H "X-Provision-Token: test-token" \
  "https://localhost/ingest/v1/tenant/test-tenant/device/dev1/telemetry" \
  -d '{"site_id":"s1","metrics":{"temp":22}}'
# Should return 202

# Test batch
curl -s --insecure -X POST \
  -H "Content-Type: application/json" \
  "https://localhost/ingest/v1/batch" \
  -d '{"messages":[{"tenant_id":"t1","device_id":"d1","msg_type":"telemetry","provision_token":"tok","site_id":"s1","metrics":{"temp":22}}]}'

# Verify message reached NATS and was processed by ingest worker
docker exec iot-nats-init nats consumer info TELEMETRY ingest-workers --server nats://iot-nats:4222
```
