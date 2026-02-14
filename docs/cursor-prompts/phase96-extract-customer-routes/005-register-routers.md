# Phase 96 — Register New Routers in app.py

## File to modify
`services/ui_iot/app.py`

## Step 1: Add imports

Find the existing router imports in app.py. They look like:

```python
from routes.customer import router as customer_router
from routes.operator import router as operator_router
# ... etc
```

Add the four new routers:

```python
from routes.devices import router as devices_router
from routes.alerts import router as alerts_router
from routes.metrics import router as metrics_router
from routes.exports import router as exports_router
```

## Step 2: Register the new routers

Find where existing routers are included. They look like:

```python
app.include_router(customer_router)
```

Add the four new routers **before** the existing `customer_router` registration:

```python
app.include_router(devices_router)
app.include_router(alerts_router)
app.include_router(metrics_router)
app.include_router(exports_router)
app.include_router(customer_router)  # existing — keep this
```

Order matters for path resolution. The new routers should come before customer_router to avoid
any potential path shadowing (unlikely since paths are different, but good practice).

## Step 3: Rebuild and restart

```bash
docker compose build ui
docker compose up -d ui
sleep 5
docker compose logs ui --tail=20 | grep -E "error|Error|ERROR|import|Import"
```

Expected: no import errors, no "module not found" errors.

## Step 4: Verify route registration

```bash
# Check FastAPI route list
curl -s http://localhost:8000/openapi.json | python3 -c "
import sys, json
spec = json.load(sys.stdin)
paths = sorted(spec['paths'].keys())
customer_paths = [p for p in paths if '/customer/' in p]
print(f'Total /customer/ paths: {len(customer_paths)}')
print('Sample:', customer_paths[:5])
"
```

The total number of `/customer/` paths should be **the same as before** (no paths added or removed).

## Step 5: Verify line counts

```bash
wc -l services/ui_iot/routes/customer.py
wc -l services/ui_iot/routes/devices.py
wc -l services/ui_iot/routes/alerts.py
wc -l services/ui_iot/routes/metrics.py
wc -l services/ui_iot/routes/exports.py
```

Expected approximate sizes:
- `customer.py`: ~1,000 lines (was 5,154)
- `devices.py`: ~1,700 lines
- `alerts.py`: ~700 lines
- `metrics.py`: ~400 lines
- `exports.py`: ~350 lines
- Total: ~4,150 lines (reduction from duplicate imports/boilerplate eliminated)
