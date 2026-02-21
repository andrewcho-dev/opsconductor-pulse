# Prompt 003 — ingest_iot /metrics Endpoint

Read `services/ingest_iot/ingest.py` — find where `counters` dict is maintained (messages_received, messages_written, messages_rejected).
Read `services/shared/metrics.py`.

## Wire Shared Metrics into ingest_iot

In `ingest.py`, replace or supplement direct counter dict increments with calls to the shared Prometheus counters:

For each message processed:
```python
from shared.metrics import ingest_messages_total, ingest_queue_depth

# On accepted message:
ingest_messages_total.labels(tenant_id=tenant_id, result="accepted").inc()

# On rejected message:
ingest_messages_total.labels(tenant_id=tenant_id, result="rejected").inc()

# On rate limited:
ingest_messages_total.labels(tenant_id=tenant_id, result="rate_limited").inc()

# Update queue depth gauge (in the queue-monitoring loop or wherever queue size is known):
ingest_queue_depth.set(current_queue_size)
```

Do NOT remove the existing `counters` dict — the `/health` endpoint still uses it. Just add the Prometheus increments alongside.

## Add /metrics Route

Add to the ingest_iot FastAPI app (find `app.py` or where routes are defined):

```python
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
from fastapi import Response

@app.get("/metrics", include_in_schema=False)
async def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
```

## Acceptance Criteria

- [ ] `ingest_messages_total` incremented on accepted/rejected/rate_limited paths
- [ ] `ingest_queue_depth` gauge updated
- [ ] GET /metrics on ingest_iot returns Prometheus format
- [ ] Existing `/health` counter dict NOT removed
- [ ] `pytest -m unit -v` passes
