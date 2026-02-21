# Phase 107b — Operator Command API (ui_iot)

## File to modify
`services/ui_iot/routes/devices.py`

Add command endpoints alongside the twin endpoints added in Phase 107.

## Pydantic models

```python
from typing import Any, Optional
from pydantic import BaseModel, Field


class CommandCreate(BaseModel):
    command_type: str = Field(..., min_length=1, max_length=100)
    command_params: dict[str, Any] = Field(default_factory=dict)
    expires_in_minutes: int = Field(default=60, ge=1, le=10080)  # max 1 week
```

---

## Endpoint 1: POST /customer/devices/{device_id}/commands

Create and dispatch a command to a device.

```python
import uuid
from datetime import datetime, timezone, timedelta

@router.post("/devices/{device_id}/commands", status_code=201)
async def send_command(
    device_id: str,
    body: CommandCreate,
    pool=Depends(get_db_pool),
    user=Depends(require_auth),
):
    tenant_id = user["tenant_id"]
    command_id = str(uuid.uuid4())
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=body.expires_in_minutes)

    async with pool.acquire() as conn:
        await set_tenant_context(conn, tenant_id)

        # Verify device exists
        exists = await conn.fetchval(
            "SELECT 1 FROM device_state WHERE tenant_id=$1 AND device_id=$2",
            tenant_id, device_id,
        )
        if not exists:
            raise HTTPException(404, "Device not found")

        # Insert command record
        await conn.execute(
            """
            INSERT INTO device_commands
              (command_id, tenant_id, device_id, command_type, command_params,
               expires_at, created_by)
            VALUES ($1,$2,$3,$4,$5,$6,$7)
            """,
            command_id, tenant_id, device_id,
            body.command_type, body.command_params,
            expires_at, user.get("sub") or user.get("user_id"),
        )

    # Publish MQTT command (non-fatal if broker is unreachable)
    # Import and call the publish function added in step 003
    from services.mqtt_sender import publish_alert
    import json as _json
    import os

    topic = f"tenant/{tenant_id}/device/{device_id}/commands"
    payload = _json.dumps({
        "command_id": command_id,
        "type": body.command_type,
        "params": body.command_params,
        "expires_at": expires_at.isoformat(),
    })

    broker_url = os.getenv("MQTT_BROKER_URL", "mqtt://iot-mqtt:1883")
    result = await publish_alert(
        broker_url=broker_url,
        topic=topic,
        payload=payload,
        qos=1,
        retain=False,
    )

    # Update published_at if MQTT succeeded
    if result.success:
        async with pool.acquire() as conn:
            await set_tenant_context(conn, tenant_id)
            await conn.execute(
                "UPDATE device_commands SET published_at=NOW(), status='queued' "
                "WHERE tenant_id=$1 AND command_id=$2",
                tenant_id, command_id,
            )

    from shared.log import get_logger
    logger = get_logger("pulse.commands")
    logger.info(
        "command_dispatched",
        extra={
            "command_id": command_id,
            "device_id": device_id,
            "command_type": body.command_type,
            "mqtt_ok": result.success,
        },
    )

    return {
        "command_id": command_id,
        "status": "queued",
        "mqtt_published": result.success,
        "expires_at": expires_at.isoformat(),
    }
```

---

## Endpoint 2: GET /customer/devices/{device_id}/commands

Returns command history for a device (most recent first).

```python
@router.get("/devices/{device_id}/commands")
async def list_device_commands(
    device_id: str,
    limit: int = Query(default=50, ge=1, le=200),
    status: Optional[str] = Query(default=None),
    pool=Depends(get_db_pool),
    user=Depends(require_auth),
):
    tenant_id = user["tenant_id"]
    async with pool.acquire() as conn:
        await set_tenant_context(conn, tenant_id)

        conditions = ["tenant_id=$1", "device_id=$2"]
        params: list = [tenant_id, device_id]

        if status:
            params.append(status)
            conditions.append(f"status=${len(params)}")

        where = " AND ".join(conditions)
        params.append(limit)

        rows = await conn.fetch(
            f"""
            SELECT command_id, command_type, command_params, status,
                   published_at, acked_at, ack_details, expires_at,
                   created_by, created_at
            FROM device_commands
            WHERE {where}
            ORDER BY created_at DESC
            LIMIT ${len(params)}
            """,
            *params,
        )

    return [dict(r) for r in rows]
```

---

## Verify

```bash
curl -s http://localhost:8000/openapi.json | \
  python3 -c "import sys,json; [print(p) for p in json.load(sys.stdin)['paths'] if 'command' in p]"
```

Expected:
```
/customer/devices/{device_id}/commands   (GET + POST)
```
