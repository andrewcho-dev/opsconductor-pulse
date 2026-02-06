# Phase 23.3: Batch Ingest Endpoint

## Task

Add `POST /ingest/v1/batch` endpoint for multi-message ingestion (up to 100 messages).

## Step 1: Add batch models and endpoint

Modify `services/ui_iot/routes/ingest.py` to add:

**Add new Pydantic models after IngestPayload:**

```python
class BatchMessage(BaseModel):
    tenant_id: str
    device_id: str
    msg_type: str
    provision_token: str
    ts: str | None = None
    site_id: str
    seq: int = 0
    metrics: dict[str, float | int | bool] = {}

class BatchRequest(BaseModel):
    messages: list[BatchMessage]

class BatchResultItem(BaseModel):
    index: int
    status: str  # "accepted" or "rejected"
    reason: str | None = None
    device_id: str | None = None

class BatchResponse(BaseModel):
    accepted: int
    rejected: int
    results: list[BatchResultItem]
```

**Add new endpoint:**

```python
@router.post("/batch")
async def ingest_batch(request: Request, batch: BatchRequest):
    """
    Ingest multiple messages in a single request.

    Max 100 messages per batch.
    Each message is validated independently.

    Returns:
        202 Accepted if any messages accepted
        400 Bad Request if all messages rejected or batch too large
    """
    if len(batch.messages) > 100:
        raise HTTPException(status_code=400, detail="Batch exceeds 100 message limit")

    if len(batch.messages) == 0:
        raise HTTPException(status_code=400, detail="Batch is empty")

    # Get shared state
    pool = await request.app.state.get_pool()
    auth_cache = request.app.state.auth_cache
    batch_writer = request.app.state.batch_writer
    rate_buckets = request.app.state.rate_buckets

    results = []
    accepted = 0
    rejected = 0

    for idx, msg in enumerate(batch.messages):
        # Validate msg_type
        if msg.msg_type not in ("telemetry", "heartbeat"):
            results.append(BatchResultItem(
                index=idx,
                status="rejected",
                reason="INVALID_MSG_TYPE",
                device_id=msg.device_id
            ))
            rejected += 1
            continue

        # Build payload dict
        payload_dict = {
            "ts": msg.ts,
            "site_id": msg.site_id,
            "seq": msg.seq,
            "metrics": msg.metrics,
        }

        result = await validate_and_prepare(
            pool=pool,
            auth_cache=auth_cache,
            rate_buckets=rate_buckets,
            tenant_id=msg.tenant_id,
            device_id=msg.device_id,
            site_id=msg.site_id,
            msg_type=msg.msg_type,
            provision_token=msg.provision_token,
            payload=payload_dict,
            max_payload_bytes=request.app.state.max_payload_bytes,
            rps=request.app.state.rps,
            burst=request.app.state.burst,
            require_token=request.app.state.require_token,
        )

        if result.success:
            await batch_writer.add(msg.tenant_id, result.line_protocol)
            results.append(BatchResultItem(
                index=idx,
                status="accepted",
                device_id=msg.device_id
            ))
            accepted += 1
        else:
            results.append(BatchResultItem(
                index=idx,
                status="rejected",
                reason=result.reason,
                device_id=msg.device_id
            ))
            rejected += 1

    status_code = 202 if accepted > 0 else 400
    return JSONResponse(
        status_code=status_code,
        content=BatchResponse(accepted=accepted, rejected=rejected, results=results).model_dump()
    )
```

## Verification

```bash
cd /home/opsconductor/simcloud/services/ui_iot && python3 -c "from routes.ingest import router; print('OK')"
```

## Files

| Action | File |
|--------|------|
| MODIFY | `services/ui_iot/routes/ingest.py` |
