# Prompt 002 — Replace `print()` in Evaluator, Dispatcher, Delivery Worker

## Your Task

Read each file fully. Replace every `print()` call with a structured logger call. Do NOT change any logic — only the logging mechanism.

### Pattern for each service

**At the top of each file**, add:
```python
from shared.logging import configure_logging, log_event
import logging

configure_logging("evaluator")  # or "dispatcher" / "delivery_worker"
logger = logging.getLogger("evaluator")
```

**Replace print() calls** following these level guidelines:

| print() content | Logger level |
|----------------|--------------|
| Normal operation ("evaluated N devices", "alert created", "dispatched") | `logger.info(msg, extra={...})` |
| Fallback/degraded mode ("fallback poll", "LISTEN setup failed") | `logger.warning(msg, extra={...})` |
| Errors, exceptions | `logger.error(msg, extra={...}, exc_info=True)` |
| Service startup ("LISTEN on ... active", "health server started") | `logger.info(msg)` |

### Add context to key events

The most important events should carry context fields:

**Evaluator — alert created:**
```python
# Before: print(f"[evaluator] evaluated {len(rows)} devices...")
logger.info("evaluation cycle complete", extra={
    "device_count": len(rows),
    "rule_count": total_rules,
    "tenant_count": len(tenant_rules_cache),
})

# Before: inside open_or_update_alert, just a counter increment
# After: the caller should log when inserted=True
logger.info("alert created", extra={
    "tenant_id": tenant_id,
    "device_id": device_id,
    "alert_type": alert_type,
    "alert_id": str(alert_id),
    "fingerprint": fingerprint,
})
```

**Dispatcher — job created:**
```python
logger.info("delivery job created", extra={
    "tenant_id": tenant_id,
    "alert_id": str(alert_id),
    "route_id": str(route_id),
})
```

**Delivery worker — delivery sent/failed:**
```python
logger.info("delivery sent", extra={
    "job_id": str(job_id),
    "integration_type": integration_type,
    "tenant_id": tenant_id,
})
logger.error("delivery failed", extra={
    "job_id": str(job_id),
    "error": str(exc),
    "attempt": attempt_number,
})
```

**LISTEN/NOTIFY log lines (all three services):**
```python
# "LISTEN on new_telemetry channel active"
logger.info("listen channel active", extra={"channel": "new_telemetry"})

# "fallback poll (no notifications received)"
logger.warning("fallback poll triggered", extra={"reason": "no notifications"})

# "WARNING: LISTEN setup failed"
logger.warning("listen setup failed, using poll-only mode", extra={"error": str(e)})
```

## Acceptance Criteria

- [ ] Zero `print()` calls remain in `evaluator.py`, `dispatcher.py`, `worker.py`
- [ ] `configure_logging("service_name")` called at startup in each file
- [ ] Key events (alert created, delivery sent/failed, listen active, fallback) have context fields
- [ ] `pytest -m unit -v` passes — 0 failures
