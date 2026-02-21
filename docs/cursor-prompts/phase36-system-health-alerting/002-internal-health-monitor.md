# Add Internal Health Monitor with System Alerts

Create a background task that monitors service health and generates operator-visible alerts when services are unhealthy.

## Overview

The UI service already polls health endpoints for the dashboard (see `services/ui_iot/routes/system.py`). This task adds:
1. A background task that runs continuously
2. Logic to create/resolve system alerts based on health status
3. Alerts visible to operators in the alert feed

## Files to Modify

### 1. services/ui_iot/app.py

Add a background task on startup that:
- Polls health endpoints every 60 seconds (configurable via env var `HEALTH_CHECK_INTERVAL`)
- For each service (ingest, evaluator, dispatcher, delivery_worker):
  - If unhealthy and no open alert exists → create system alert
  - If healthy and open alert exists → resolve the alert
- Use existing health check logic from `routes/system.py` (the `_check_health` function)

```python
# Pseudocode structure:
@app.on_event("startup")
async def start_health_monitor():
    asyncio.create_task(health_monitor_loop())

async def health_monitor_loop():
    while True:
        await asyncio.sleep(HEALTH_CHECK_INTERVAL)
        for service_name, url in HEALTH_ENDPOINTS.items():
            is_healthy = await check_service_health(url)
            await update_system_alert(service_name, is_healthy)
```

### 2. services/ui_iot/db/queries.py (or new file db/system_alerts.py)

Add functions:

```python
async def get_open_system_alert(conn, service_name: str) -> dict | None:
    """Check if there's an open system alert for this service."""

async def create_system_alert(conn, service_name: str, message: str) -> None:
    """Create a new system alert with severity CRITICAL."""

async def resolve_system_alert(conn, service_name: str) -> None:
    """Mark the system alert as resolved."""
```

### 3. Database consideration

System alerts can use the existing `alerts` table with:
- `tenant_id = '__system__'` (special value for system-wide alerts)
- `device_id = NULL` or a placeholder like `'system'`
- `severity = 'CRITICAL'`
- `message = 'Service unhealthy: {service_name}'`

OR create a separate `system_alerts` table if you want different schema.

## Alert Behavior

| Service State | Alert Action |
|--------------|--------------|
| Was healthy, now unhealthy | Create alert: "Service {name} is unhealthy" |
| Was unhealthy, still unhealthy | No action (alert already exists) |
| Was unhealthy, now healthy | Resolve alert, add resolution note |
| Was healthy, still healthy | No action |

## Environment Variables

```
HEALTH_CHECK_INTERVAL=60  # seconds between health checks
SYSTEM_ALERT_ENABLED=true # toggle to disable
```

## Operator Visibility

System alerts should appear in:
1. The operator alert feed (`/app/operator/alerts`)
2. The system dashboard as a notification/banner
3. Optionally: trigger webhook/email via existing integration routes

## Constraints

- Do not duplicate health check logic — reuse from `routes/system.py`
- Use async/await patterns consistent with existing codebase
- Handle database connection failures gracefully (log, retry later)
- Avoid alert storms — deduplicate by checking for existing open alert
