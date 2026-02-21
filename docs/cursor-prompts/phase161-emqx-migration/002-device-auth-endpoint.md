# Task 2: HTTP Auth Backend Endpoint for Device Authentication

## Files to Create/Modify

- **Create:** `services/ui_iot/routes/internal.py` — new internal-only route module
- **Modify:** `services/ui_iot/app.py` — register the internal router

## What to Do

EMQX calls our API on every device CONNECT and PUBLISH/SUBSCRIBE to validate authentication and authorization. We need two endpoints that EMQX's HTTP auth/ACL plugins will call.

### Step 1: Create the internal routes module

Create `services/ui_iot/routes/internal.py`:

```python
"""
Internal endpoints called by EMQX for MQTT authentication and authorization.
These are NOT exposed to external clients — only reachable on the Docker network.
"""

import os
import logging
import hashlib
from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel
from db.pool import operator_connection
from dependencies import get_db_pool

logger = logging.getLogger("internal")

INTERNAL_AUTH_SECRET = os.getenv("MQTT_INTERNAL_AUTH_SECRET", "")

router = APIRouter(
    prefix="/api/v1/internal",
    tags=["internal"],
)


def _verify_internal(x_internal_auth: str = Header(...)):
    """Verify request comes from EMQX (shared secret)."""
    if not INTERNAL_AUTH_SECRET or x_internal_auth != INTERNAL_AUTH_SECRET:
        raise HTTPException(status_code=403, detail="Forbidden")


# ─── Models ───────────────────────────────────────────


class AuthRequest(BaseModel):
    username: str
    client_id: str | None = None
    peer_cert_cn: str | None = None


class AuthResponse(BaseModel):
    result: str  # "allow" | "deny" | "ignore"
    is_superuser: bool = False


class AclRequest(BaseModel):
    username: str
    topic: str
    action: str  # "publish" | "subscribe"
    client_id: str | None = None


class AclResponse(BaseModel):
    result: str  # "allow" | "deny"


# ─── Auth Endpoint ────────────────────────────────────


@router.post("/mqtt-auth")
async def mqtt_authenticate(
    body: AuthRequest,
    x_internal_auth: str = Header(""),
):
    """
    Called by EMQX on every CONNECT.

    For certificate-authenticated devices:
      - peer_cert_cn = "{tenant_id}/{device_id}"
      - Validate cert exists in device_certificates table

    For password-authenticated clients:
      - Built-in database handles service_pulse
      - Return "ignore" to let EMQX check next auth provider
    """
    _verify_internal(x_internal_auth)

    # Certificate-authenticated device
    cn = body.peer_cert_cn or body.username
    if cn and "/" in cn:
        parts = cn.split("/", 1)
        if len(parts) == 2:
            tenant_id, device_id = parts

            pool = await get_db_pool()
            async with operator_connection(pool) as conn:
                # Check device exists and has active certificate
                has_cert = await conn.fetchval(
                    """
                    SELECT 1 FROM device_certificates
                    WHERE tenant_id = $1
                      AND device_id = $2
                      AND status = 'ACTIVE'
                      AND not_after > now()
                    LIMIT 1
                    """,
                    tenant_id, device_id,
                )

                if has_cert:
                    # Also verify device is not revoked
                    device_status = await conn.fetchval(
                        "SELECT status FROM device_registry WHERE tenant_id = $1 AND device_id = $2",
                        tenant_id, device_id,
                    )
                    if device_status and device_status != "REVOKED":
                        return AuthResponse(result="allow")
                    else:
                        logger.warning("mqtt_auth_denied_revoked", extra={
                            "tenant_id": tenant_id, "device_id": device_id,
                        })
                        return AuthResponse(result="deny")

            # Cert CN looks like tenant/device but no active cert found
            logger.warning("mqtt_auth_denied_no_cert", extra={"cn": cn})
            return AuthResponse(result="deny")

    # Not a cert device — let EMQX built-in database handle it
    return AuthResponse(result="ignore")


# ─── ACL Endpoint ─────────────────────────────────────


@router.post("/mqtt-acl")
async def mqtt_authorize(
    body: AclRequest,
    x_internal_auth: str = Header(""),
):
    """
    Called by EMQX on every PUBLISH and SUBSCRIBE.

    Rules:
    - service_pulse: allow all (superuser in built-in DB, but double-check here)
    - Certificate devices: only allow topics matching their tenant_id/device_id
    """
    _verify_internal(x_internal_auth)

    username = body.username

    # Superuser (internal service account)
    if username == "service_pulse":
        return AclResponse(result="allow")

    # Certificate-authenticated device: CN = "{tenant_id}/{device_id}"
    if "/" in username:
        parts = username.split("/", 1)
        if len(parts) == 2:
            cert_tenant, cert_device = parts

            # Parse the topic to extract tenant_id and device_id
            topic_parts = body.topic.split("/")
            if (
                len(topic_parts) >= 4
                and topic_parts[0] == "tenant"
                and topic_parts[2] == "device"
            ):
                topic_tenant = topic_parts[1]
                topic_device = topic_parts[3]

                # Enforce: device can only access its own tenant/device topics
                if topic_tenant == cert_tenant and topic_device == cert_device:
                    return AclResponse(result="allow")

            # Topic doesn't match device identity
            logger.warning("mqtt_acl_denied", extra={
                "username": username,
                "topic": body.topic,
                "action": body.action,
                "reason": "topic_tenant_device_mismatch",
            })
            return AclResponse(result="deny")

    # Unknown user type — deny by default
    return AclResponse(result="deny")
```

### Step 2: Register the internal router

In `services/ui_iot/app.py`, import and include the internal router:

```python
from routes.internal import router as internal_router
app.include_router(internal_router)
```

Add it near the other `include_router` calls.

### Step 3: Add MQTT_INTERNAL_AUTH_SECRET to docker-compose

In the `ui` service environment in `compose/docker-compose.yml`:

```yaml
      MQTT_INTERNAL_AUTH_SECRET: "${MQTT_INTERNAL_AUTH_SECRET}"
```

### Step 4: Ensure Caddy does NOT expose internal endpoints

Check `compose/caddy/Caddyfile` — the `/api/v1/internal/*` routes should NOT be proxied to the outside world. If Caddy proxies all `/api/*` routes, add an exclusion:

```
# Block internal endpoints from external access
@internal path /api/v1/internal/*
respond @internal 404
```

## Important Notes

- **Performance:** EMQX caches auth/ACL results by default (configurable TTL). Not every PUBLISH will hit our API — only cache misses. This keeps the load reasonable.
- **Shared secret:** The `X-Internal-Auth` header prevents external clients from calling these endpoints even if Caddy misconfiguration exposes them.
- **operator_connection:** We use `operator_connection()` (bypasses RLS) because this endpoint validates devices across all tenants — it's not a tenant-scoped request.
- **Deny by default:** If auth returns "deny" or an error, EMQX disconnects the client. This is the safe default.
- **This closes the read-side ACL gap:** Previously, Mosquitto's `pattern read tenant/+/device/+/shadow/desired` allowed any device to read any tenant's shadow. Now, the ACL endpoint checks `topic_tenant == cert_tenant` for every subscribe operation.
- **Provision token auth:** If devices also authenticate via provision tokens (not just certs), extend the auth endpoint to accept and validate tokens. For now, this focuses on certificate-based auth since that's the primary device auth mechanism on port 8883.

## Verification

```bash
# Test auth endpoint directly
curl -s -X POST http://localhost:8080/api/v1/internal/mqtt-auth \
  -H "Content-Type: application/json" \
  -H "X-Internal-Auth: ${MQTT_INTERNAL_AUTH_SECRET}" \
  -d '{"username": "tenant-a/device-001", "peer_cert_cn": "tenant-a/device-001"}' | jq .

# Test ACL endpoint
curl -s -X POST http://localhost:8080/api/v1/internal/mqtt-acl \
  -H "Content-Type: application/json" \
  -H "X-Internal-Auth: ${MQTT_INTERNAL_AUTH_SECRET}" \
  -d '{"username": "tenant-a/device-001", "topic": "tenant/tenant-a/device/device-001/telemetry", "action": "publish"}' | jq .

# Test cross-tenant denial
curl -s -X POST http://localhost:8080/api/v1/internal/mqtt-acl \
  -H "Content-Type: application/json" \
  -H "X-Internal-Auth: ${MQTT_INTERNAL_AUTH_SECRET}" \
  -d '{"username": "tenant-a/device-001", "topic": "tenant/tenant-b/device/device-001/telemetry", "action": "subscribe"}' | jq .
# Should return {"result": "deny"}
```
