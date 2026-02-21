# Phase 107b — Device HTTP ACK Endpoint (ingest_iot)

## Context

MQTT ACK (step 003) covers devices that speak MQTT. This step adds an HTTP
ACK endpoint for devices that only use HTTP — same auth model as the twin
and jobs device APIs.

## File to modify
`services/ingest_iot/ingest.py`

Add alongside the existing `/device/v1/shadow` and `/device/v1/jobs` endpoints.

---

## Endpoint: POST /device/v1/commands/{command_id}/ack

```python
from pydantic import BaseModel
from typing import Any, Optional


class CommandAckPayload(BaseModel):
    status: str = "ok"          # "ok" | "error"
    details: Optional[dict[str, Any]] = None


@router.post("/device/v1/commands/{command_id}/ack")
async def device_ack_command(
    command_id: str,
    body: CommandAckPayload,
    request: Request,
    pool=Depends(get_ingest_pool),
):
    token = request.headers.get("X-Provision-Token")
    if not token:
        raise HTTPException(401, "Missing provision token")
    tenant_id, device_id = await resolve_device(token, pool)

    async with pool.acquire() as conn:
        updated = await conn.execute(
            """
            UPDATE device_commands
            SET status      = 'delivered',
                acked_at    = NOW(),
                ack_details = $1
            WHERE tenant_id  = $2
              AND command_id = $3
              AND device_id  = $4
              AND status     = 'queued'
            """,
            {"status": body.status, "details": body.details},
            tenant_id, command_id, device_id,
        )

    if updated == "UPDATE 0":
        # Either not found, wrong device, or already acked — not an error
        raise HTTPException(404, "Command not found or already acknowledged")

    return {"command_id": command_id, "acknowledged": True}
```

---

## Endpoint: GET /device/v1/commands/pending

Optional — allows HTTP-only devices to poll for pending commands the same way
they poll for jobs. Useful for devices that don't subscribe to MQTT at all.

```python
@router.get("/device/v1/commands/pending")
async def device_get_pending_commands(
    request: Request,
    pool=Depends(get_ingest_pool),
):
    token = request.headers.get("X-Provision-Token")
    if not token:
        raise HTTPException(401, "Missing provision token")
    tenant_id, device_id = await resolve_device(token, pool)

    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT command_id, command_type, command_params, expires_at, created_at
            FROM device_commands
            WHERE tenant_id = $1
              AND device_id = $2
              AND status    = 'queued'
              AND expires_at > NOW()
            ORDER BY created_at ASC
            LIMIT 20
            """,
            tenant_id, device_id,
        )

    return {
        "commands": [
            {
                "command_id": r["command_id"],
                "type": r["command_type"],
                "params": dict(r["command_params"]),
                "expires_at": r["expires_at"].isoformat(),
            }
            for r in rows
        ]
    }
```

---

## Verify endpoints registered

```bash
curl -s http://localhost:<ingest_port>/openapi.json | \
  python3 -c "import sys,json; [print(p) for p in json.load(sys.stdin)['paths'] if 'command' in p]"
```

Expected:
```
/device/v1/commands/pending
/device/v1/commands/{command_id}/ack
```
