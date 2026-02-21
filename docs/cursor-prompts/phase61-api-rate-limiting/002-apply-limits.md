# Prompt 002 — Apply Rate Limits to Customer Router

Read `services/ui_iot/routes/customer.py` — find the router and a few representative endpoints.
Read `services/ui_iot/app.py` to confirm `limiter` is importable.

## Apply Rate Limiting

Import the limiter in customer.py:

```python
from services.ui_iot.app import limiter  # adjust import path to match project structure
import os

CUSTOMER_RATE_LIMIT = os.environ.get("RATE_LIMIT_CUSTOMER", "100/minute")
```

Apply the decorator to the **router-level** using a dependency, OR apply it to the most latency-sensitive endpoints individually. The recommended approach for FastAPI + slowapi is to apply at the route level:

```python
@router.get("/devices")
@limiter.limit(CUSTOMER_RATE_LIMIT)
async def list_devices(request: Request, ...):
    ...
```

Apply `@limiter.limit(CUSTOMER_RATE_LIMIT)` to these endpoints:
- GET /customer/devices
- GET /customer/alerts
- POST /customer/alert-rule-templates/apply

Note: `slowapi` requires `request: Request` as a parameter in rate-limited routes. Add it if not present.

Do NOT apply rate limits to:
- GET /healthz
- GET /metrics
- Operator routes (/operator/*)
- WebSocket endpoints

## Acceptance Criteria

- [ ] `@limiter.limit(CUSTOMER_RATE_LIMIT)` on GET /devices, GET /alerts, POST /apply
- [ ] `request: Request` parameter present on each limited route
- [ ] Operator and health endpoints NOT rate-limited
- [ ] `pytest -m unit -v` passes
