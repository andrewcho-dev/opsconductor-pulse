# Task 001 -- Message Routing Rules

## Commit

```
feat(phase130): add message routing rules table, API, and ingest fan-out
```

## What This Task Does

1. Creates a `message_routes` table with RLS for tenant-scoped message routing configuration.
2. Adds a new route file `services/ui_iot/routes/message_routing.py` with full CRUD + test endpoint.
3. Modifies the ingest worker (`services/ingest_iot/ingest.py`) to evaluate message routes after writing telemetry, match topics against MQTT wildcard patterns, apply optional payload filters, and fan out to configured destinations (webhook, mqtt_republish, postgresql).

---

## Step 1: Database Migration

Create file: `db/migrations/081_message_routes.sql`

```sql
-- Migration 081: Message routing rules for telemetry fan-out
-- Customers define rules that match MQTT topics and optionally filter
-- by payload content, then route matched messages to external destinations.

CREATE TABLE IF NOT EXISTS message_routes (
    id              SERIAL PRIMARY KEY,
    tenant_id       TEXT NOT NULL,
    name            VARCHAR(100) NOT NULL,
    topic_filter    VARCHAR(200) NOT NULL,
    destination_type VARCHAR(20) NOT NULL
                     CHECK (destination_type IN ('webhook', 'mqtt_republish', 'postgresql')),
    destination_config JSONB NOT NULL DEFAULT '{}',
    payload_filter  JSONB,
    is_enabled      BOOLEAN NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_message_routes_tenant
    ON message_routes (tenant_id, is_enabled);

CREATE INDEX IF NOT EXISTS idx_message_routes_tenant_topic
    ON message_routes (tenant_id) WHERE is_enabled = TRUE;

-- RLS
ALTER TABLE message_routes ENABLE ROW LEVEL SECURITY;
ALTER TABLE message_routes FORCE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation_policy ON message_routes
    FOR ALL TO pulse_app
    USING (tenant_id = current_setting('app.tenant_id', true))
    WITH CHECK (tenant_id = current_setting('app.tenant_id', true));

-- Grant permissions
GRANT SELECT, INSERT, UPDATE, DELETE ON message_routes TO pulse_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON message_routes TO pulse_operator;
GRANT USAGE ON SEQUENCE message_routes_id_seq TO pulse_app;
GRANT USAGE ON SEQUENCE message_routes_id_seq TO pulse_operator;

COMMENT ON TABLE message_routes IS 'Tenant-scoped message routing rules for telemetry fan-out to external destinations';
COMMENT ON COLUMN message_routes.topic_filter IS 'MQTT topic pattern with + (single-level) and # (multi-level) wildcards';
COMMENT ON COLUMN message_routes.payload_filter IS 'Optional JSONPath-like filter expressions, e.g. {"temperature": {"$gt": 80}}';
COMMENT ON COLUMN message_routes.destination_type IS 'Delivery target: webhook (HTTP POST), mqtt_republish (forward to MQTT topic), postgresql (default write)';
```

---

## Step 2: API Routes

Create file: `services/ui_iot/routes/message_routing.py`

### Router Setup

```python
import json
import logging
import re
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional, Literal

from dependencies import get_db_pool
from db.pool import tenant_connection
from middleware.auth import JWTBearer
from middleware.tenant import inject_tenant_context, require_customer, get_tenant_id

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/customer",
    tags=["message-routing"],
    dependencies=[
        Depends(JWTBearer()),
        Depends(inject_tenant_context),
        Depends(require_customer),
    ],
)
```

### Pydantic Models

```python
class MessageRouteCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    topic_filter: str = Field(..., min_length=1, max_length=200)
    destination_type: Literal["webhook", "mqtt_republish", "postgresql"]
    destination_config: dict = Field(default_factory=dict)
    payload_filter: Optional[dict] = None
    is_enabled: bool = True


class MessageRouteUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    topic_filter: Optional[str] = Field(default=None, min_length=1, max_length=200)
    destination_type: Optional[Literal["webhook", "mqtt_republish", "postgresql"]] = None
    destination_config: Optional[dict] = None
    payload_filter: Optional[dict] = None
    is_enabled: Optional[bool] = None


class TestRouteRequest(BaseModel):
    topic: str = "tenant/test/device/DEV-001/telemetry"
    payload: dict = Field(default_factory=lambda: {"metrics": {"temperature": 90}})
```

### Topic Validation

Validate that topic_filter is a valid MQTT pattern:

```python
MQTT_TOPIC_PATTERN = re.compile(r'^[a-zA-Z0-9_/+#-]+$')

def validate_topic_filter(topic_filter: str) -> None:
    """Validate MQTT topic filter syntax."""
    if not MQTT_TOPIC_PATTERN.match(topic_filter):
        raise HTTPException(400, "Invalid topic filter: contains illegal characters")
    parts = topic_filter.split("/")
    for i, part in enumerate(parts):
        if part == "#" and i != len(parts) - 1:
            raise HTTPException(400, "Invalid topic filter: # wildcard must be last segment")
        if "+" in part and part != "+":
            raise HTTPException(400, "Invalid topic filter: + must occupy entire segment")
        if "#" in part and part != "#":
            raise HTTPException(400, "Invalid topic filter: # must occupy entire segment")
```

### Destination Config Validation

```python
def validate_destination_config(destination_type: str, config: dict) -> None:
    """Validate destination_config has required keys."""
    if destination_type == "webhook":
        if "url" not in config:
            raise HTTPException(422, "webhook destination requires 'url' in destination_config")
    elif destination_type == "mqtt_republish":
        if "topic" not in config:
            raise HTTPException(422, "mqtt_republish destination requires 'topic' in destination_config")
    # postgresql has no required config (it is the default write behavior)
```

### Endpoints

```python
@router.get("/message-routes")
async def list_message_routes(
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    pool=Depends(get_db_pool),
):
    tenant_id = get_tenant_id()
    async with tenant_connection(pool, tenant_id) as conn:
        rows = await conn.fetch(
            """
            SELECT id, tenant_id, name, topic_filter, destination_type,
                   destination_config, payload_filter, is_enabled, created_at, updated_at
            FROM message_routes
            WHERE tenant_id = $1
            ORDER BY created_at DESC
            LIMIT $2 OFFSET $3
            """,
            tenant_id, limit, offset,
        )
        total = await conn.fetchval(
            "SELECT COUNT(*) FROM message_routes WHERE tenant_id = $1",
            tenant_id,
        )
    return {
        "routes": [dict(r) for r in rows],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.post("/message-routes", status_code=201)
async def create_message_route(body: MessageRouteCreate, pool=Depends(get_db_pool)):
    tenant_id = get_tenant_id()
    validate_topic_filter(body.topic_filter)
    validate_destination_config(body.destination_type, body.destination_config)

    async with tenant_connection(pool, tenant_id) as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO message_routes
                (tenant_id, name, topic_filter, destination_type, destination_config,
                 payload_filter, is_enabled)
            VALUES ($1, $2, $3, $4, $5::jsonb, $6::jsonb, $7)
            RETURNING id, tenant_id, name, topic_filter, destination_type,
                      destination_config, payload_filter, is_enabled, created_at, updated_at
            """,
            tenant_id,
            body.name.strip(),
            body.topic_filter,
            body.destination_type,
            json.dumps(body.destination_config),
            json.dumps(body.payload_filter) if body.payload_filter else None,
            body.is_enabled,
        )
    return dict(row)


@router.put("/message-routes/{route_id}")
async def update_message_route(route_id: int, body: MessageRouteUpdate, pool=Depends(get_db_pool)):
    tenant_id = get_tenant_id()
    if body.topic_filter is not None:
        validate_topic_filter(body.topic_filter)
    if body.destination_type is not None and body.destination_config is not None:
        validate_destination_config(body.destination_type, body.destination_config)

    async with tenant_connection(pool, tenant_id) as conn:
        existing = await conn.fetchrow(
            "SELECT * FROM message_routes WHERE tenant_id = $1 AND id = $2",
            tenant_id, route_id,
        )
        if not existing:
            raise HTTPException(404, "Message route not found")

        # Build dynamic UPDATE -- only set provided fields
        updates = {}
        if body.name is not None:
            updates["name"] = body.name.strip()
        if body.topic_filter is not None:
            updates["topic_filter"] = body.topic_filter
        if body.destination_type is not None:
            updates["destination_type"] = body.destination_type
        if body.destination_config is not None:
            updates["destination_config"] = json.dumps(body.destination_config)
        if body.payload_filter is not None:
            updates["payload_filter"] = json.dumps(body.payload_filter)
        if body.is_enabled is not None:
            updates["is_enabled"] = body.is_enabled

        if not updates:
            return dict(existing)

        set_clauses = []
        params = [tenant_id, route_id]
        for i, (col, val) in enumerate(updates.items(), start=3):
            suffix = "::jsonb" if col in ("destination_config", "payload_filter") else ""
            set_clauses.append(f"{col} = ${i}{suffix}")
            params.append(val)

        set_clauses.append("updated_at = NOW()")
        set_sql = ", ".join(set_clauses)

        row = await conn.fetchrow(
            f"""
            UPDATE message_routes
            SET {set_sql}
            WHERE tenant_id = $1 AND id = $2
            RETURNING id, tenant_id, name, topic_filter, destination_type,
                      destination_config, payload_filter, is_enabled, created_at, updated_at
            """,
            *params,
        )
    if not row:
        raise HTTPException(404, "Message route not found")
    return dict(row)


@router.delete("/message-routes/{route_id}", status_code=204)
async def delete_message_route(route_id: int, pool=Depends(get_db_pool)):
    tenant_id = get_tenant_id()
    async with tenant_connection(pool, tenant_id) as conn:
        res = await conn.execute(
            "DELETE FROM message_routes WHERE tenant_id = $1 AND id = $2",
            tenant_id, route_id,
        )
    if res.endswith("0"):
        raise HTTPException(404, "Message route not found")
    from fastapi.responses import Response
    return Response(status_code=204)


@router.post("/message-routes/{route_id}/test")
async def test_message_route(route_id: int, body: TestRouteRequest, pool=Depends(get_db_pool)):
    """Test a message route with a sample payload (dry-run delivery)."""
    tenant_id = get_tenant_id()
    async with tenant_connection(pool, tenant_id) as conn:
        route = await conn.fetchrow(
            "SELECT * FROM message_routes WHERE tenant_id = $1 AND id = $2",
            tenant_id, route_id,
        )
    if not route:
        raise HTTPException(404, "Message route not found")

    # Check topic match
    matched = mqtt_topic_matches(route["topic_filter"], body.topic)

    # Check payload filter
    filter_passed = True
    if matched and route["payload_filter"]:
        filter_passed = evaluate_payload_filter(route["payload_filter"], body.payload)

    result = {
        "route_id": route_id,
        "topic_matched": matched,
        "filter_passed": filter_passed,
        "would_deliver": matched and filter_passed,
        "destination_type": route["destination_type"],
    }

    # Optionally attempt actual delivery if would_deliver is true
    if matched and filter_passed and route["destination_type"] == "webhook":
        try:
            import httpx
            config = route["destination_config"] or {}
            url = config.get("url")
            if url:
                async with httpx.AsyncClient(timeout=5.0) as client:
                    resp = await client.post(url, json={"test": True, **body.payload})
                result["delivery_status"] = resp.status_code
                result["delivery_success"] = 200 <= resp.status_code < 300
        except Exception as exc:
            result["delivery_status"] = None
            result["delivery_error"] = str(exc)

    return result
```

### Register Router

In `services/ui_iot/app.py`, add:

```python
from routes.message_routing import router as message_routing_router
# ... in the router registration block (after line ~186):
app.include_router(message_routing_router)
```

---

## Step 3: MQTT Topic Matching Utility

Create file: `services/ingest_iot/topic_matcher.py`

This is a standalone module used by both the ingest worker and the API test endpoint.

```python
"""MQTT topic matching with + and # wildcards.

+ matches exactly one topic level.
# matches zero or more remaining levels (must be last segment).

Examples:
    mqtt_topic_matches("tenant/+/device/+/telemetry", "tenant/T1/device/D1/telemetry")  -> True
    mqtt_topic_matches("tenant/+/device/#", "tenant/T1/device/D1/telemetry")             -> True
    mqtt_topic_matches("tenant/T1/device/D1/telemetry", "tenant/T2/device/D1/telemetry") -> False
"""
import re
from functools import lru_cache


@lru_cache(maxsize=1024)
def _compile_topic_regex(topic_filter: str) -> re.Pattern:
    """Convert MQTT topic filter to compiled regex.

    + -> [^/]+    (one level)
    # -> .*       (zero or more levels, must be last)
    """
    parts = topic_filter.split("/")
    regex_parts = []
    for i, part in enumerate(parts):
        if part == "+":
            regex_parts.append("[^/]+")
        elif part == "#":
            # # matches the rest of the topic (zero or more levels)
            regex_parts.append(".*")
            break  # # must be last
        else:
            regex_parts.append(re.escape(part))
    pattern = "^" + "/".join(regex_parts) + "$"
    return re.compile(pattern)


def mqtt_topic_matches(topic_filter: str, topic: str) -> bool:
    """Check if an MQTT topic matches a topic filter with wildcards."""
    regex = _compile_topic_regex(topic_filter)
    return regex.match(topic) is not None
```

Also add to `services/ui_iot/routes/message_routing.py` a local copy of the matching function (or create a shared utility in `shared/`). The simplest approach is to duplicate the two functions `mqtt_topic_matches` and `_compile_topic_regex` into the route file, since the ingest service and UI service are separate containers.

---

## Step 4: Payload Filter Evaluation

Add this function to both `services/ingest_iot/topic_matcher.py` and the message_routing route file:

```python
def evaluate_payload_filter(filter_spec: dict, payload: dict) -> bool:
    """Evaluate a simple payload filter against a message payload.

    Supports operators at the top level of the filter_spec:
        {"temperature": {"$gt": 80}}         -> payload["metrics"]["temperature"] > 80
        {"humidity": {"$lt": 50}}             -> payload["metrics"]["humidity"] < 50
        {"temperature": {"$gte": 70, "$lte": 100}}  -> range check
        {"device_type": "sensor"}             -> exact match on payload field

    Looks for values in payload["metrics"] first, then payload root.
    All conditions must match (AND logic).
    """
    if not filter_spec:
        return True

    metrics = payload.get("metrics", {}) or {}

    for key, condition in filter_spec.items():
        # Resolve value: check metrics first, then payload root
        value = metrics.get(key)
        if value is None:
            value = payload.get(key)
        if value is None:
            return False  # Key not found -> filter fails

        if isinstance(condition, dict):
            # Operator-based filter
            for op, threshold in condition.items():
                try:
                    value_num = float(value)
                    threshold_num = float(threshold)
                except (TypeError, ValueError):
                    return False

                if op == "$gt" and not (value_num > threshold_num):
                    return False
                elif op == "$gte" and not (value_num >= threshold_num):
                    return False
                elif op == "$lt" and not (value_num < threshold_num):
                    return False
                elif op == "$lte" and not (value_num <= threshold_num):
                    return False
                elif op == "$eq" and not (value_num == threshold_num):
                    return False
                elif op == "$ne" and not (value_num != threshold_num):
                    return False
        else:
            # Exact match
            if str(value) != str(condition):
                return False

    return True
```

---

## Step 5: Ingest Worker Integration

Modify `services/ingest_iot/ingest.py` to evaluate message routes after successful telemetry write.

### 5a. Add imports at the top of ingest.py

```python
import httpx
from topic_matcher import mqtt_topic_matches, evaluate_payload_filter
```

### 5b. Add a message route cache to the Ingestor class

In `Ingestor.__init__`, add:

```python
self._message_routes_cache: dict[str, list] = {}  # tenant_id -> [route_rows]
self._routes_cache_ts: dict[str, float] = {}       # tenant_id -> last_refresh_time
self._routes_cache_ttl = 30  # seconds
```

### 5c. Add route loading method

Add to the `Ingestor` class:

```python
async def _get_message_routes(self, tenant_id: str) -> list:
    """Get enabled message routes for a tenant (cached)."""
    now = time.time()
    last_refresh = self._routes_cache_ts.get(tenant_id, 0)
    if now - last_refresh < self._routes_cache_ttl:
        return self._message_routes_cache.get(tenant_id, [])

    assert self.pool is not None
    async with self.pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT id, topic_filter, destination_type, destination_config, payload_filter
            FROM message_routes
            WHERE tenant_id = $1 AND is_enabled = TRUE
            """,
            tenant_id,
        )
    routes = [dict(r) for r in rows]
    self._message_routes_cache[tenant_id] = routes
    self._routes_cache_ts[tenant_id] = now
    return routes
```

### 5d. Add delivery method

Add to the `Ingestor` class:

```python
async def _deliver_to_route(
    self, route: dict, topic: str, payload: dict, tenant_id: str
) -> None:
    """Deliver a message to a route destination."""
    dest_type = route["destination_type"]
    config = route.get("destination_config") or {}

    if dest_type == "webhook":
        url = config.get("url")
        if not url:
            return
        method = config.get("method", "POST").upper()
        headers = {"Content-Type": "application/json"}

        # HMAC signing if secret is configured
        body_bytes = json.dumps(payload).encode()
        secret = config.get("secret")
        if secret:
            import hashlib
            import hmac as hmac_mod
            sig = hmac_mod.new(secret.encode(), body_bytes, hashlib.sha256).hexdigest()
            headers["X-Signature-SHA256"] = sig

        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.request(method, url, content=body_bytes, headers=headers)
            if resp.status_code >= 400:
                raise Exception(f"Webhook returned HTTP {resp.status_code}")

    elif dest_type == "mqtt_republish":
        republish_topic = config.get("topic")
        if not republish_topic:
            return
        # Replace template variables in the target topic
        republish_topic = republish_topic.replace("{tenant_id}", tenant_id)
        republish_topic = republish_topic.replace("{device_id}", payload.get("device_id", ""))
        # Use the MQTT client to republish
        # The MQTT client is on the main thread; schedule via loop
        if self.loop and hasattr(self, '_mqtt_client') and self._mqtt_client:
            msg_bytes = json.dumps(payload).encode()
            self._mqtt_client.publish(republish_topic, msg_bytes)

    elif dest_type == "postgresql":
        pass  # Already written by the batch writer
```

### 5e. Add fan-out after telemetry write

In the `db_worker` method, **after** the successful `await self.batch_writer.add(record)` call (around line 1119), add:

```python
# --- Message route fan-out ---
try:
    routes = await self._get_message_routes(tenant_id)
    for route in routes:
        try:
            if not mqtt_topic_matches(route["topic_filter"], topic):
                continue
            if route.get("payload_filter"):
                pf = route["payload_filter"]
                if isinstance(pf, str):
                    pf = json.loads(pf)
                if not evaluate_payload_filter(pf, payload):
                    continue
            if route["destination_type"] == "postgresql":
                continue  # Already written

            await self._deliver_to_route(route, topic, payload, tenant_id)
            logger.debug(
                "route_delivered",
                extra={"route_id": route["id"], "destination": route["destination_type"]},
            )
        except Exception as route_exc:
            # Delivery failed -- will be handled by DLQ in task 002
            logger.warning(
                "route_delivery_failed",
                extra={
                    "route_id": route["id"],
                    "error": str(route_exc),
                    "destination": route["destination_type"],
                },
            )
except Exception as route_fan_exc:
    logger.warning("route_fanout_error", extra={"error": str(route_fan_exc)})
```

### 5f. Store MQTT client reference

In the `run()` method, after creating the MQTT client (line ~1369), store a reference:

```python
self._mqtt_client = client
```

---

## Step 6: Add httpx Dependency

Ensure `httpx` is in the ingest service dependencies. Check `services/ingest_iot/requirements.txt` (or the Dockerfile / pyproject.toml). If not present, add:

```
httpx>=0.27.0
```

---

## Verification

```bash
# Apply migration
psql -h localhost -U iot -d iotcloud -f db/migrations/081_message_routes.sql

# Create a route
curl -s -X POST http://localhost:8080/customer/message-routes \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -H "X-CSRF-Token: $CSRF" \
  -d '{
    "name": "Forward all telemetry to webhook",
    "topic_filter": "tenant/+/device/+/telemetry",
    "destination_type": "webhook",
    "destination_config": {"url": "https://webhook.site/YOUR-UUID"},
    "is_enabled": true
  }' | jq .

# List routes
curl -s http://localhost:8080/customer/message-routes \
  -H "Authorization: Bearer $TOKEN" | jq .

# Test route with sample payload
curl -s -X POST http://localhost:8080/customer/message-routes/1/test \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -H "X-CSRF-Token: $CSRF" \
  -d '{
    "topic": "tenant/TENANT1/device/DEV-001/telemetry",
    "payload": {"metrics": {"temperature": 90}}
  }' | jq .

# Send real telemetry via MQTT
mosquitto_pub -h localhost -p 1883 \
  -t "tenant/TENANT1/device/DEV-001/telemetry" \
  -m '{"ts":"2026-02-16T00:00:00Z","site_id":"SITE-1","provision_token":"test","metrics":{"temperature":95}}'

# Check webhook.site to verify delivery

# Verify topic matching edge cases
# + matches single level:   tenant/+/device/+/telemetry  matches  tenant/T1/device/D1/telemetry
# # matches multi-level:    tenant/+/device/#             matches  tenant/T1/device/D1/telemetry
# Exact match only:         tenant/T1/device/D1/telemetry  does NOT match  tenant/T2/device/D1/telemetry
```
