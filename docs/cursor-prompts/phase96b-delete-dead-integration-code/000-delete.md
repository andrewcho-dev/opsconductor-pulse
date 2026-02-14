# Phase 96b — Delete Dead Integration Code from customer.py

## Problem

`services/ui_iot/routes/customer.py` is 2,719 lines. Lines ~1094–2719 are dead code:
all the old `/integrations`, `/integration-routes`, and `/delivery-jobs` endpoints that were
supposed to be removed in Phase 95. The underlying tables (`integrations`, `integration_routes`,
`delivery_jobs`, `delivery_attempts`) were dropped in migration 071 — these endpoints query
tables that no longer exist.

## What to delete

Open `services/ui_iot/routes/customer.py` and delete ALL functions with these routes:

### Integration endpoints (all variants)
- `GET /integrations`
- `GET /integrations/snmp`
- `GET /integrations/snmp/{integration_id}`
- `POST /integrations/snmp`
- `PATCH /integrations/snmp/{integration_id}`
- `DELETE /integrations/snmp/{integration_id}`
- `GET /integrations/email`
- `GET /integrations/email/{integration_id}`
- `POST /integrations/email`
- `PATCH /integrations/email/{integration_id}`
- `DELETE /integrations/email/{integration_id}`
- `GET /integrations/mqtt`
- `GET /integrations/mqtt/{integration_id}`
- `POST /integrations/mqtt`
- `PATCH /integrations/mqtt/{integration_id}`
- `DELETE /integrations/mqtt/{integration_id}`
- `POST /integrations` (generic create)
- `GET /integrations/{integration_id}`
- `PATCH /integrations/{integration_id}`
- `GET /integrations/{integration_id}/template-variables`
- `DELETE /integrations/{integration_id}`
- `POST /integrations/{integration_id}/test`
- `POST /integrations/{integration_id}/test-send`

### Integration route endpoints
- `GET /integration-routes`
- `GET /integration-routes/{route_id}`
- `POST /integration-routes`
- `PATCH /integration-routes/{route_id}`
- `DELETE /integration-routes/{route_id}`

### Delivery job endpoints
- `GET /delivery-jobs`
- `GET /delivery-jobs/{job_id}/attempts`

## Also remove dead imports

After deleting the functions, search the top of the file for imports that are now unused:

```python
# Remove any of these if they are no longer used elsewhere in customer.py:
from pydantic import BaseModel  # keep if still used
SNMPIntegrationResponse         # remove
EmailIntegrationResponse        # remove
MQTTIntegrationResponse         # remove
# any dispatch_to_integration, AlertPayload imports
```

Search for each import with Ctrl+F to confirm it's not used by the remaining code before removing.

## Verify line count

```bash
wc -l services/ui_iot/routes/customer.py
```

Expected: approximately **1,000–1,100 lines** (was 2,719).

## Rebuild and verify no 404/500 regressions

```bash
docker compose -f compose/docker-compose.yml build ui
docker compose -f compose/docker-compose.yml up -d ui
sleep 5
docker compose -f compose/docker-compose.yml logs ui --tail=20 | grep -i error

# Confirm surviving endpoints still work (should return 401 not 404/500)
curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/customer/sites
curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/customer/subscriptions
curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/customer/geocode

# Confirm dead endpoints are gone (should return 404)
curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/customer/integrations
curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/customer/integration-routes
curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/customer/delivery-jobs
```

Expected: first three return 401 (auth required), last three return 404 (route gone).

## OpenAPI path count

```bash
curl -s http://localhost:8000/openapi.json | python3 -c "
import sys, json
spec = json.load(sys.stdin)
paths = sorted(spec['paths'].keys())
old = [p for p in paths if 'integrations' in p or 'delivery-jobs' in p or 'integration-routes' in p]
print('Old dead paths remaining:', old)
print('Total /customer/ paths:', len([p for p in paths if '/customer/' in p]))
"
```

Expected: `Old dead paths remaining: []` — none of the old paths survive.

## Commit

```bash
git add services/ui_iot/routes/customer.py
git commit -m "refactor: delete dead integration/delivery-job endpoints from customer.py

Tables integrations, integration_routes, delivery_jobs were dropped in migration 071.
These ~1600 lines of endpoint code were querying non-existent tables.
customer.py reduced from 2719 → ~1000 lines.
All notification/delivery is now handled by notification_channels + notification_jobs."

git push origin main
git log --oneline -3
```
