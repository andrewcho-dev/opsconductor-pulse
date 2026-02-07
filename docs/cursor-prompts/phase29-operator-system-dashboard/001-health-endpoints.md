# Phase 29.1: Add Health Check Endpoints to Services

## Task

Add `/health` endpoints to services that don't have them, and enhance existing ones to return useful metrics.

---

## Ingest Service

**File:** `services/ingest_iot/ingest.py`

Add health endpoint that exposes internal counters:

```python
from aiohttp import web

# Add global counters (if not already present)
COUNTERS = {
    "messages_received": 0,
    "messages_written": 0,
    "messages_rejected": 0,
    "queue_depth": 0,
    "last_write_at": None,
}

async def health_handler(request):
    """Health check endpoint with metrics."""
    return web.json_response({
        "status": "healthy",
        "service": "ingest",
        "counters": {
            "messages_received": COUNTERS["messages_received"],
            "messages_written": COUNTERS["messages_written"],
            "messages_rejected": COUNTERS["messages_rejected"],
            "queue_depth": COUNTERS["queue_depth"],
        },
        "last_write_at": COUNTERS["last_write_at"],
    })

# Add to aiohttp app setup (or create minimal HTTP server if not present)
# app.router.add_get("/health", health_handler)
```

If the service doesn't have an HTTP server, add a minimal one on port 8080:

```python
async def start_health_server():
    app = web.Application()
    app.router.add_get("/health", health_handler)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", 8080)
    await site.start()
    logger.info("Health server started on port 8080")
```

---

## Evaluator Service

**File:** `services/evaluator_iot/evaluator.py`

Add health endpoint:

```python
COUNTERS = {
    "rules_evaluated": 0,
    "alerts_created": 0,
    "evaluation_errors": 0,
    "last_evaluation_at": None,
}

async def health_handler(request):
    return web.json_response({
        "status": "healthy",
        "service": "evaluator",
        "counters": {
            "rules_evaluated": COUNTERS["rules_evaluated"],
            "alerts_created": COUNTERS["alerts_created"],
            "evaluation_errors": COUNTERS["evaluation_errors"],
        },
        "last_evaluation_at": COUNTERS["last_evaluation_at"],
    })
```

---

## Dispatcher Service

**File:** `services/dispatcher/dispatcher.py`

Add health endpoint:

```python
COUNTERS = {
    "alerts_processed": 0,
    "routes_matched": 0,
    "jobs_queued": 0,
    "last_dispatch_at": None,
}

async def health_handler(request):
    return web.json_response({
        "status": "healthy",
        "service": "dispatcher",
        "counters": {
            "alerts_processed": COUNTERS["alerts_processed"],
            "routes_matched": COUNTERS["routes_matched"],
            "jobs_queued": COUNTERS["jobs_queued"],
        },
        "last_dispatch_at": COUNTERS["last_dispatch_at"],
    })
```

---

## Delivery Worker Service

**File:** `services/delivery_worker/worker.py`

Add health endpoint:

```python
COUNTERS = {
    "jobs_processed": 0,
    "jobs_succeeded": 0,
    "jobs_failed": 0,
    "jobs_pending": 0,
    "last_delivery_at": None,
}

async def health_handler(request):
    return web.json_response({
        "status": "healthy",
        "service": "delivery_worker",
        "counters": {
            "jobs_processed": COUNTERS["jobs_processed"],
            "jobs_succeeded": COUNTERS["jobs_succeeded"],
            "jobs_failed": COUNTERS["jobs_failed"],
            "jobs_pending": COUNTERS["jobs_pending"],
        },
        "last_delivery_at": COUNTERS["last_delivery_at"],
    })
```

---

## Update Docker Compose

**File:** `compose/docker-compose.yml`

Expose health ports for internal access (no external port mapping needed):

```yaml
  ingest:
    # ... existing config ...
    expose:
      - "8080"
    healthcheck:
      test: ["CMD-SHELL", "curl -sf http://localhost:8080/health || exit 1"]
      interval: 10s
      timeout: 5s
      retries: 3

  evaluator:
    # ... existing config ...
    expose:
      - "8080"
    healthcheck:
      test: ["CMD-SHELL", "curl -sf http://localhost:8080/health || exit 1"]
      interval: 10s
      timeout: 5s
      retries: 3

  dispatcher:
    # ... existing config ...
    expose:
      - "8080"
    healthcheck:
      test: ["CMD-SHELL", "curl -sf http://localhost:8080/health || exit 1"]
      interval: 10s
      timeout: 5s
      retries: 3

  delivery_worker:
    # ... existing config ...
    expose:
      - "8080"
    healthcheck:
      test: ["CMD-SHELL", "curl -sf http://localhost:8080/health || exit 1"]
      interval: 10s
      timeout: 5s
      retries: 3
```

---

## Increment Counters

Update each service to increment counters at appropriate points:

**Ingest**: Increment on message receive, write success, rejection
**Evaluator**: Increment on rule evaluation, alert creation
**Dispatcher**: Increment on alert processing, route matching
**Delivery**: Increment on job processing, success, failure

Example for ingest:
```python
# When message is received
COUNTERS["messages_received"] += 1

# When written to InfluxDB
COUNTERS["messages_written"] += 1
COUNTERS["last_write_at"] = datetime.utcnow().isoformat()

# When rejected
COUNTERS["messages_rejected"] += 1
```

---

## Verification

```bash
# Rebuild services
cd /home/opsconductor/simcloud/compose
docker compose build ingest evaluator dispatcher delivery_worker
docker compose up -d

# Test health endpoints (from inside the network)
docker compose exec ui curl http://iot-ingest:8080/health
docker compose exec ui curl http://iot-evaluator:8080/health
docker compose exec ui curl http://iot-dispatcher:8080/health
docker compose exec ui curl http://iot-delivery-worker:8080/health
```

---

## Files

| Action | File |
|--------|------|
| MODIFY | `services/ingest_iot/ingest.py` |
| MODIFY | `services/evaluator_iot/evaluator.py` |
| MODIFY | `services/dispatcher/dispatcher.py` |
| MODIFY | `services/delivery_worker/worker.py` |
| MODIFY | `compose/docker-compose.yml` |
