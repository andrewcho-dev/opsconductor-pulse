# Prompt 004 — evaluator_iot /metrics Endpoint

Read `services/evaluator_iot/evaluator.py` — find where evaluation counts are tracked.
Read `services/shared/metrics.py`.

## Wire Shared Metrics into evaluator_iot

In `evaluator.py`, add Prometheus counter increments:

```python
from shared.metrics import (
    evaluator_rules_evaluated_total,
    evaluator_alerts_created_total,
    evaluator_evaluation_errors_total,
)

# In the rule evaluation loop, after evaluating each rule:
evaluator_rules_evaluated_total.labels(tenant_id=tenant_id).inc()

# When open_or_update_alert() creates/updates an alert:
evaluator_alerts_created_total.labels(tenant_id=tenant_id).inc()

# In exception handlers:
evaluator_evaluation_errors_total.inc()
```

Do NOT remove existing in-memory counters.

## Add /metrics Route

Find where the evaluator exposes its HTTP health endpoint (likely a small FastAPI or aiohttp app alongside the main loop). Add:

```python
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST

@app.get("/metrics", include_in_schema=False)
async def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
```

If the evaluator has no HTTP app, add a minimal one:
```python
# In main() startup, alongside existing health endpoint setup:
from fastapi import FastAPI
metrics_app = FastAPI()

@metrics_app.get("/metrics")
async def metrics():
    from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
```

## Acceptance Criteria

- [ ] `evaluator_rules_evaluated_total` incremented per rule evaluated
- [ ] `evaluator_alerts_created_total` incremented on alert create/update
- [ ] `evaluator_evaluation_errors_total` incremented on exceptions
- [ ] GET /metrics on evaluator_iot returns Prometheus format
- [ ] `pytest -m unit -v` passes
