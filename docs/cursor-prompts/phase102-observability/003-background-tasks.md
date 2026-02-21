# Phase 102 — Trace IDs in Background Task Ticks

## Pattern

Every background task tick should:
1. Generate a UUID trace_id at the start of the tick.
2. Set `trace_id_var` via ContextVar so all log lines in that tick carry it.
3. Reset the ContextVar in a `finally` block.

```python
import uuid
from shared.log import trace_id_var, get_logger

logger = get_logger(__name__)

async def run_my_tick(pool):
    token = trace_id_var.set(str(uuid.uuid4()))
    try:
        logger.info("tick_start", extra={"tick": "my_tick"})
        # ... tick logic ...
        logger.info("tick_done", extra={"tick": "my_tick"})
    except Exception as exc:
        logger.exception("tick_error", extra={"tick": "my_tick", "error": str(exc)})
    finally:
        trace_id_var.reset(token)
```

## Files to modify

### services/evaluator/evaluator.py

Find the main evaluation tick function (the one that queries for pending
alerts and fires `run_evaluation` per device). Wrap it with the pattern above.

### services/ops_worker/worker.py

Find `run_escalation_tick` and `run_report_tick`. Wrap each with the pattern.
Each tick gets its own UUID — they run independently.

### services/delivery_worker/worker.py

Find the delivery poll loop / tick. Wrap with the pattern.

## docker-compose.yml — add SERVICE_NAME env var

In `compose/docker-compose.yml`, add `SERVICE_NAME` to each service's
`environment` section:

```yaml
services:
  iot-ui:
    environment:
      SERVICE_NAME: ui_iot

  iot-ingest:
    environment:
      SERVICE_NAME: ingest_iot

  iot-evaluator:
    environment:
      SERVICE_NAME: evaluator

  iot-ops-worker:
    environment:
      SERVICE_NAME: ops_worker

  iot-delivery-worker:
    environment:
      SERVICE_NAME: delivery_worker
```

Add these alongside existing env vars — do not remove any existing entries.
