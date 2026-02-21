# Prompt 003 — Replace `print()` in Ingest, Ops Worker, Provision API

## Your Task

Same pattern as prompt 002. Read each file fully, replace print() with structured logger.

### `services/ingest_iot/ingest.py`

```python
configure_logging("ingest")
logger = logging.getLogger("ingest")
```

Key events with context:

```python
# Device authenticated / message accepted
logger.info("telemetry accepted", extra={
    "tenant_id": tenant_id,
    "device_id": device_id,
    "msg_type": msg_type,
    "metrics_count": len(metrics),
})

# Message rejected (quarantined)
logger.warning("message quarantined", extra={
    "reason": rejection_reason,
    "tenant_id": tenant_id,
    "device_id": device_id,  # may be None if unknown device
})

# Rate limited
logger.warning("rate limited", extra={
    "tenant_id": tenant_id,
    "device_id": device_id,
    "reason": "rate_limit_exceeded",
})

# Batch writer flush
logger.debug("batch flushed", extra={"row_count": n})
```

### `services/ops_worker/health_monitor.py`

```python
configure_logging("ops_worker")
logger = logging.getLogger("ops_worker.health_monitor")
```

Key events:
```python
logger.info("health check complete", extra={
    "service": service_name,
    "status": "healthy",  # or "unhealthy"
    "response_ms": elapsed_ms,
})

logger.warning("service unhealthy", extra={
    "service": service_name,
    "error": str(exc),
})
```

### `services/ops_worker/metrics_collector.py`

```python
logger = logging.getLogger("ops_worker.metrics_collector")

logger.debug("metrics collected", extra={"metric_count": n})
logger.error("metrics collection failed", extra={"error": str(exc)}, exc_info=True)
```

### `services/ops_worker/main.py`

```python
configure_logging("ops_worker")  # call this once at startup, before both loops start
```

### `services/provision_api/`

**Read the provision_api main file.** Apply the same pattern:
```python
configure_logging("provision_api")
logger = logging.getLogger("provision_api")
```

Replace any print() calls. Key events:
```python
logger.info("device provisioned", extra={
    "tenant_id": tenant_id,
    "device_id": device_id,
})
logger.warning("provision attempt failed", extra={
    "reason": reason,
    "activation_code_prefix": activation_code[:4] + "...",  # never log full token
})
```

## Security Note

Never log full provision tokens, passwords, or secrets. Log only prefixes (first 4 chars + "...") or omit entirely.

## Acceptance Criteria

- [ ] Zero `print()` calls in ingest_iot, ops_worker, provision_api service files
- [ ] `configure_logging()` called at startup in each service
- [ ] No secrets logged (tokens, passwords)
- [ ] `pytest -m unit -v` passes
