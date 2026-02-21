# Task 2: Health/Readiness/Liveness Probes

## Files to Modify

All services that expose HTTP endpoints.

## What to Do

Ensure all services have proper `/health` and `/ready` endpoints for K8s probes.

### Ingest Service (`services/ingest_iot/ingest.py`)

Already has `/health` endpoint. Add `/ready`:

```python
# /health — liveness (is the process alive and not deadlocked?)
# Returns 200 if the event loop is responding

# /ready — readiness (can this pod accept work?)
# Returns 200 if NATS is connected AND DB pool is available
# Returns 503 if not ready
```

Readiness check should verify:
- `self._nc is not None and self._nc.is_connected` (NATS connection alive)
- `self.pool is not None` (DB pool initialized)
- `self.batch_writer is not None and self.batch_writer._running` (batch writer active)

### Route Delivery Service (`services/route_delivery/delivery.py`)

Add a simple health server (same pattern as ingest):

```python
from aiohttp import web

async def health_handler(request):
    return web.json_response({"status": "ok", "delivered": svc.delivered, "failed": svc.failed})

async def ready_handler(request):
    if svc._nc and svc._nc.is_connected and svc._pool:
        return web.json_response({"status": "ready"})
    return web.json_response({"status": "not_ready"}, status=503)

async def start_health_server():
    app = web.Application()
    app.router.add_get("/health", health_handler)
    app.router.add_get("/ready", ready_handler)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", 8080)
    await site.start()
```

### All Other Services

| Service | Has /health? | Needs /ready? |
|---------|-------------|---------------|
| ingest | Yes | Add (NATS + DB check) |
| evaluator | Yes | Add (DB + notify listener check) |
| ui_iot | Yes (FastAPI) | Already handled by FastAPI startup |
| ops_worker | Yes | Add (DB check) |
| route-delivery | Create | Create |
| keycloak | Built-in | Built-in (`/health/ready`) |
| EMQX | Built-in | Built-in (`emqx ctl status`) |
| NATS | Built-in | Built-in (`/healthz`) |

### Probe Configuration in Helm Templates

For each deployment, use this pattern:

```yaml
livenessProbe:
  httpGet:
    path: /health
    port: 8080
  initialDelaySeconds: 10
  periodSeconds: 30
  timeoutSeconds: 5
  failureThreshold: 3

readinessProbe:
  httpGet:
    path: /ready
    port: 8080
  initialDelaySeconds: 5
  periodSeconds: 10
  timeoutSeconds: 3
  failureThreshold: 2

startupProbe:
  httpGet:
    path: /health
    port: 8080
  initialDelaySeconds: 5
  periodSeconds: 5
  failureThreshold: 30   # Allow up to 150s for startup
```

## Important Notes

- **Liveness** = "is the process alive?" → restart if unhealthy
- **Readiness** = "can this pod accept traffic?" → remove from service if not ready
- **Startup** = "is the process still initializing?" → don't check liveness/readiness until startup passes
- Don't make liveness probes too aggressive — a slow DB query shouldn't cause a restart cascade
