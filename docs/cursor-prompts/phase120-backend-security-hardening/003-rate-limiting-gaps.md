# 003: Rate-Limiting Gaps

## Context

The application uses **slowapi** for HTTP rate limiting. The limiter is initialized in `services/ui_iot/routes/customer.py` (line 100):

```python
limiter = Limiter(key_func=get_rate_limit_key, headers_enabled=True)
CUSTOMER_RATE_LIMIT = os.environ.get("RATE_LIMIT_CUSTOMER", "100/minute")
```

It is attached to `app.state.limiter` in `app.py` (line 123) and the `SlowAPIMiddleware` is added at line 131.

Currently, only three endpoints use `@limiter.limit()`:
- `routes/devices.py` line 531: `GET /customer/devices` -- `CUSTOMER_RATE_LIMIT` (100/min)
- `routes/alerts.py` line 72: `GET /customer/alerts` -- `CUSTOMER_RATE_LIMIT` (100/min)
- `routes/alerts.py` line 277: `POST /customer/alert-rule-templates/apply` -- `CUSTOMER_RATE_LIMIT` (100/min)

Several heavy or destructive endpoints have NO rate limits. Additionally, `GET /ingest/v1/metrics/rate-limits` (ingest.py line 97-104) is completely unauthenticated -- it exposes rate-limit stats to anyone.

## Step 1: Add Rate Limits to Heavy/Destructive Endpoints

### File: `services/ui_iot/routes/devices.py`

The file uses `from routes.customer import *` which already imports `limiter`, `CUSTOMER_RATE_LIMIT`, and `Request`. The `@limiter.limit()` decorator must come **after** the `@router.*` decorator.

For slowapi, the endpoint function MUST accept a `request: Request` parameter (slowapi extracts the key from it). Check each endpoint -- if it does not already have `request: Request`, add it.

**Telemetry export** -- heavy CSV generation, up to 10,000 rows:

```python
# Line 756-757:
# BEFORE:
@router.get("/devices/{device_id}/telemetry/export", dependencies=[Depends(require_customer)])
async def export_telemetry_csv(
    device_id: str,
    range: str = Query("24h"),
    limit: int = Query(5000, ge=1, le=10000),
    pool=Depends(get_db_pool),
):

# AFTER:
@router.get("/devices/{device_id}/telemetry/export", dependencies=[Depends(require_customer)])
@limiter.limit("5/minute")
async def export_telemetry_csv(
    request: Request,
    device_id: str,
    range: str = Query("24h"),
    limit: int = Query(5000, ge=1, le=10000),
    pool=Depends(get_db_pool),
):
```

**Device creation** -- provisioning new devices:

```python
# Line 101:
# BEFORE:
@router.post("/devices", status_code=201)
async def create_device(device: DeviceCreate, pool=Depends(get_db_pool)):

# AFTER:
@router.post("/devices", status_code=201)
@limiter.limit("30/minute")
async def create_device(request: Request, device: DeviceCreate, pool=Depends(get_db_pool)):
```

**Device deletion** -- destructive operation:

```python
# Line 620:
# BEFORE:
@router.delete("/devices/{device_id}")
async def delete_device(device_id: str, pool=Depends(get_db_pool)):

# AFTER:
@router.delete("/devices/{device_id}")
@limiter.limit("10/minute")
async def delete_device(request: Request, device_id: str, pool=Depends(get_db_pool)):
```

**Device import** -- bulk operation:

```python
# Line 264:
# BEFORE:
@router.post("/devices/import")
async def import_devices_csv(file: UploadFile = File(...), pool=Depends(get_db_pool)):

# AFTER:
@router.post("/devices/import")
@limiter.limit("5/minute")
async def import_devices_csv(request: Request, file: UploadFile = File(...), pool=Depends(get_db_pool)):
```

**Device decommission** -- destructive:

```python
# Line 924:
# BEFORE:
@router.patch("/devices/{device_id}/decommission", dependencies=[Depends(require_customer)])
async def decommission_device(device_id: str, pool=Depends(get_db_pool)):

# AFTER:
@router.patch("/devices/{device_id}/decommission", dependencies=[Depends(require_customer)])
@limiter.limit("10/minute")
async def decommission_device(request: Request, device_id: str, pool=Depends(get_db_pool)):
```

### File: `services/ui_iot/routes/notifications.py`

This file does NOT currently import `limiter` or `Request` from the routes.customer module (it uses its own imports). Add the necessary imports:

After line 6 (`from fastapi import APIRouter, Depends, HTTPException, Query, Response`), ensure `Request` is imported:
```python
from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
```

Add the limiter import after line 12 (`from middleware.tenant import ...`):
```python
from routes.customer import limiter
```

Apply rate limits to notification channel write endpoints:

```python
# Line 120 - POST /notification-channels
@router.post("/notification-channels", response_model=ChannelOut, status_code=201)
@limiter.limit("20/minute")
async def create_channel(request: Request, body: ChannelIn, pool=Depends(get_db_pool)):

# Line 162 - PUT /notification-channels/{channel_id}
@router.put("/notification-channels/{channel_id}", response_model=ChannelOut)
@limiter.limit("20/minute")
async def update_channel(request: Request, channel_id: int, body: ChannelIn, pool=Depends(get_db_pool)):

# Line 188 - DELETE /notification-channels/{channel_id}
@router.delete("/notification-channels/{channel_id}", status_code=204)
@limiter.limit("20/minute")
async def delete_channel(request: Request, channel_id: int, pool=Depends(get_db_pool)):

# Line 202 - POST /notification-channels/{channel_id}/test
@router.post("/notification-channels/{channel_id}/test")
@limiter.limit("5/minute")
async def test_channel(request: Request, channel_id: int, pool=Depends(get_db_pool)):

# Line 272 - POST /notification-routing-rules
@router.post("/notification-routing-rules", response_model=RoutingRuleOut, status_code=201)
@limiter.limit("20/minute")
async def create_routing_rule(request: Request, body: RoutingRuleIn, pool=Depends(get_db_pool)):

# Line 302 - PUT /notification-routing-rules/{rule_id}
@router.put("/notification-routing-rules/{rule_id}", response_model=RoutingRuleOut)
@limiter.limit("20/minute")
async def update_routing_rule(request: Request, rule_id: int, body: RoutingRuleIn, pool=Depends(get_db_pool)):

# Line 336 - DELETE /notification-routing-rules/{rule_id}
@router.delete("/notification-routing-rules/{rule_id}", status_code=204)
@limiter.limit("20/minute")
async def delete_routing_rule(request: Request, rule_id: int, pool=Depends(get_db_pool)):
```

### File: `services/ui_iot/routes/escalation.py`

Add imports. After line 5 (`from fastapi import APIRouter, Depends, HTTPException, Response`), add `Request`:
```python
from fastapi import APIRouter, Depends, HTTPException, Request, Response
```

After line 11 (`from dependencies import get_db_pool`), add:
```python
from routes.customer import limiter
```

Apply to write endpoints:

```python
# Line 104 - POST /escalation-policies
@router.post("/escalation-policies", response_model=EscalationPolicyOut, status_code=201)
@limiter.limit("20/minute")
async def create_escalation_policy(request: Request, body: EscalationPolicyIn, pool=Depends(get_db_pool)):

# Line 154 - PUT /escalation-policies/{policy_id}
@router.put("/escalation-policies/{policy_id}", response_model=EscalationPolicyOut)
@limiter.limit("20/minute")
async def update_escalation_policy(request: Request, policy_id: int, body: EscalationPolicyIn, pool=Depends(get_db_pool)):

# Line 207 - DELETE /escalation-policies/{policy_id}
@router.delete("/escalation-policies/{policy_id}", status_code=204)
@limiter.limit("20/minute")
async def delete_escalation_policy(request: Request, policy_id: int, pool=Depends(get_db_pool)):
```

### File: `services/ui_iot/routes/oncall.py`

Add imports. After line 4 (`from fastapi import APIRouter, Depends, HTTPException, Query, Response`), add `Request`:
```python
from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
```

After line 11 (`from oncall.resolver import ...`), add:
```python
from routes.customer import limiter
```

Apply to write endpoints:

```python
# Line 94 - POST /oncall-schedules
@router.post("/oncall-schedules", status_code=201)
@limiter.limit("20/minute")
async def create_schedule(request: Request, body: OncallScheduleIn, pool=Depends(get_db_pool)):

# Line 140 - PUT /oncall-schedules/{schedule_id}
@router.put("/oncall-schedules/{schedule_id}")
@limiter.limit("20/minute")
async def update_schedule(request: Request, schedule_id: int, body: OncallScheduleIn, pool=Depends(get_db_pool)):

# Line 184 - DELETE /oncall-schedules/{schedule_id}
@router.delete("/oncall-schedules/{schedule_id}", status_code=204)
@limiter.limit("20/minute")
async def delete_schedule(request: Request, schedule_id: int, pool=Depends(get_db_pool)):
```

## Step 2: Add Auth to Ingest Rate-Limit Stats Endpoint

### File: `services/ui_iot/routes/ingest.py`

The endpoint at **lines 97-104** is on the `/ingest/v1` router which has NO auth dependencies:

```python
# Line 22:
router = APIRouter(prefix="/ingest/v1", tags=["ingest"])
```

The rate-limit stats endpoint exposes internal rate-limiting configuration and statistics. It should require authentication.

Add auth imports after line 17 (`from shared.sampled_logger import get_sampled_logger`):
```python
from middleware.auth import JWTBearer
from fastapi import Depends
```

**Note**: `Depends` may already be available if imported via FastAPI. Check the existing imports at line 7.

Modify the endpoint to require authentication:

```python
# BEFORE (lines 97-104):
@router.get("/metrics/rate-limits")
async def rate_limit_stats():
    """Return rate limiting statistics for monitoring."""
    rate_limiter = get_rate_limiter()
    return {
        "rate_limit_stats": rate_limiter.get_stats(),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

# AFTER:
@router.get("/metrics/rate-limits", dependencies=[Depends(JWTBearer())])
async def rate_limit_stats():
    """Return rate limiting statistics for monitoring."""
    rate_limiter = get_rate_limiter()
    return {
        "rate_limit_stats": rate_limiter.get_stats(),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
```

This ensures only authenticated users can see rate-limit internals. No tenant context is needed since this is a global diagnostic endpoint.

## Verification

```bash
# 1. Test telemetry export rate limit
for i in $(seq 1 7); do
  echo "Request $i:"
  curl -s -o /dev/null -w "%{http_code}\n" \
    -H "Authorization: Bearer $TOKEN" \
    "http://localhost:8080/customer/devices/test-device/telemetry/export?range=24h"
done
# First 5 should return 200, requests 6-7 should return 429

# 2. Test device creation rate limit
for i in $(seq 1 35); do
  echo "Request $i:"
  curl -s -o /dev/null -w "%{http_code}\n" \
    -X POST \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d "{\"device_id\": \"rate-test-$i\", \"site_id\": \"test\"}" \
    "http://localhost:8080/customer/devices"
done
# First 30 should return 201 or 4xx (validation), requests 31+ should return 429

# 3. Test notification channel write rate limit
for i in $(seq 1 22); do
  curl -s -o /dev/null -w "%{http_code}\n" \
    -X POST \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d '{"name": "test", "channel_type": "slack", "config": {"webhook_url": "https://example.com"}}' \
    "http://localhost:8080/customer/notification-channels"
done
# First 20 should return 201, requests 21+ should return 429

# 4. Test rate-limit stats endpoint requires auth
curl -s -o /dev/null -w "%{http_code}\n" \
  "http://localhost:8080/ingest/v1/metrics/rate-limits"
# Expected: 401 (was 200 before)

curl -s -o /dev/null -w "%{http_code}\n" \
  -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8080/ingest/v1/metrics/rate-limits"
# Expected: 200

# 5. Verify 429 responses include Retry-After header
# The RateLimitExceeded handler in app.py (lines 216-223) already sets Retry-After.

# 6. Run tests
cd services/ui_iot && python -m pytest tests/ -x -q
```

## Notes

- The slowapi `@limiter.limit()` decorator uses the key function defined at `routes/customer.py` line 100 (`get_rate_limit_key`). Check what this function returns -- typically `request.client.host` or a user identifier from the token. The rate limit is per-key, so if keyed by IP, all users behind the same NAT share a limit.
- The `RateLimitExceeded` exception handler is already in `app.py` at lines 216-223 and returns a proper 429 with `Retry-After`.
- For endpoints that already had `request: Request` as a parameter, no change is needed to the signature -- just add the decorator.
- For endpoints that did NOT have `request: Request`, it must be added as the first parameter (before path parameters and body).
