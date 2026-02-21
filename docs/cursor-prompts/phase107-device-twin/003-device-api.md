# Phase 107 — Device-Facing Twin API (ingest_iot)

## Context

These endpoints are called by devices, not operators. Authentication is via
`X-Provision-Token` header (same as HTTP telemetry ingestion). They live in
`services/ingest_iot` — do NOT add them to ui_iot.

## Step 1: Find the existing HTTP ingest handler in ingest_iot

```bash
grep -rn "provision_token\|X-Provision-Token\|FastAPI\|APIRouter" \
  services/ingest_iot/ --include="*.py" -l
```

Read whichever file contains the HTTP ingestion route to understand the
auth pattern (how `provision_token` is validated and `tenant_id`/`device_id`
are resolved). The new twin endpoints use the same auth.

## Step 2: Add a device auth helper if one doesn't exist

If `ingest_iot` doesn't have a reusable function to validate a provision
token and return `(tenant_id, device_id)`, add one:

```python
async def resolve_device(token: str, pool) -> tuple[str, str]:
    """
    Validates provision token. Returns (tenant_id, device_id).
    Raises HTTPException 401 if invalid.
    """
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT tenant_id, device_id
            FROM device_state
            WHERE provision_token_hash = encode(
                digest($1, 'sha256'), 'hex'
            )
            """,
            token,
        )
    if row is None:
        raise HTTPException(status_code=401, detail="Invalid provision token")
    return row["tenant_id"], row["device_id"]
```

If this logic already exists, use it — do not duplicate it.

## Step 3: GET /device/v1/shadow — device pulls desired state

Device calls this to get the current desired state and its version.
Device should call this on startup and periodically if it doesn't use MQTT.

```python
@router.get("/device/v1/shadow")
async def device_get_shadow(
    request: Request,
    pool=Depends(get_ingest_pool),
):
    token = request.headers.get("X-Provision-Token")
    if not token:
        raise HTTPException(status_code=401, detail="Missing provision token")
    tenant_id, device_id = await resolve_device(token, pool)

    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT desired_state, desired_version
            FROM device_state
            WHERE tenant_id = $1 AND device_id = $2
            """,
            tenant_id, device_id,
        )

    return {
        "desired": dict(row["desired_state"]),
        "version": row["desired_version"],
    }
```

## Step 4: POST /device/v1/shadow/reported — device reports actual state

Device calls this after applying the desired config. It reports its actual
current state and the version it was responding to.

```python
from pydantic import BaseModel
from typing import Any

class ReportedStatePayload(BaseModel):
    reported: dict[str, Any]
    version: int   # the desired_version the device is acknowledging


@router.post("/device/v1/shadow/reported")
async def device_report_shadow(
    body: ReportedStatePayload,
    request: Request,
    pool=Depends(get_ingest_pool),
):
    token = request.headers.get("X-Provision-Token")
    if not token:
        raise HTTPException(status_code=401, detail="Missing provision token")
    tenant_id, device_id = await resolve_device(token, pool)

    async with pool.acquire() as conn:
        # Only update reported_version if it's advancing (no rollback)
        await conn.execute(
            """
            UPDATE device_state
            SET reported_state   = $1,
                reported_version = GREATEST(reported_version, $2),
                last_seen        = NOW()
            WHERE tenant_id = $3 AND device_id = $4
            """,
            body.reported, body.version, tenant_id, device_id,
        )

    return {"accepted": True, "version": body.version}
```

## Step 5: Register new routes

In `services/ingest_iot/ingest.py` (or wherever the FastAPI app/router is
built), register the new router or add the endpoints.

Confirm the new paths are accessible:

```bash
# From outside the container — adjust port to match ingest_iot's exposed port
curl -s http://localhost:<ingest_port>/openapi.json | \
  python3 -c "import sys,json; [print(p) for p in json.load(sys.stdin)['paths'] if 'shadow' in p]"
```

Expected:
```
/device/v1/shadow
/device/v1/shadow/reported
```

## Step 6: Confirm auth rejects bad tokens

```bash
curl -s -X GET http://localhost:<ingest_port>/device/v1/shadow \
  -H "X-Provision-Token: tok-invalid" | python3 -m json.tool
```

Expected: `{"detail": "Invalid provision token"}` with HTTP 401.
