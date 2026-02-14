# Phase 96 — Verify: Route Extraction

## Step 1: Route count sanity check

Before and after counts must match exactly.

**Before** (run this before starting phase 96 and save the output):
```bash
curl -s http://localhost:8000/openapi.json | python3 -c "
import sys, json
spec = json.load(sys.stdin)
paths = spec['paths'].keys()
print(len([p for p in paths if '/customer/' in p]), 'customer paths')
"
```

**After** (run this after all routers are registered):
```bash
curl -s http://localhost:8000/openapi.json | python3 -c "
import sys, json
spec = json.load(sys.stdin)
paths = spec['paths'].keys()
print(len([p for p in paths if '/customer/' in p]), 'customer paths')
"
```

Both numbers must be **identical**.

## Step 2: Smoke test one endpoint from each new file

```bash
TOKEN="<customer_jwt>"

# devices.py
curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/customer/devices \
  -H "Authorization: Bearer $TOKEN"
# Expected: 200

# alerts.py
curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/customer/alerts \
  -H "Authorization: Bearer $TOKEN"
# Expected: 200

# metrics.py
curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/customer/metrics/catalog \
  -H "Authorization: Bearer $TOKEN"
# Expected: 200

# exports.py
curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/customer/audit-log \
  -H "Authorization: Bearer $TOKEN"
# Expected: 200
```

## Step 3: Run unit tests

```bash
docker compose run --rm ui pytest tests/unit/ -v --tb=short 2>&1 | tail -30
```

Expected: same pass rate as before the extraction. No new failures.

## Step 4: Line count verification

```bash
wc -l services/ui_iot/routes/*.py | sort -n
```

Expected: `customer.py` is the smallest or second-smallest file (it was the largest).

## Step 5: Verify no circular imports

```bash
docker compose logs ui --tail=5 | grep -i "circular\|ImportError\|cannot import"
# Expected: no output (no circular import errors)
```

## Step 6: Commit

```bash
git add services/ui_iot/routes/ services/ui_iot/app.py

git commit -m "refactor: extract customer.py into domain route files (devices, alerts, metrics, exports)

- routes/devices.py: device CRUD, tokens, uptime, tags, groups, maintenance windows (~1700 lines)
- routes/alerts.py: alert CRUD, alert rules, templates, digest settings (~700 lines)
- routes/metrics.py: metric catalog, normalized metrics, metric mappings (~400 lines)
- routes/exports.py: CSV export, reports, report runs, audit log, delivery status (~350 lines)
- routes/customer.py: reduced from 5154 to ~1000 lines (sites, subscriptions, delivery jobs)
- app.py: register 4 new routers
- Zero behavior change: all route paths and response schemas are identical"

git push origin main
git log --oneline -3
```

## Definition of Done

- [ ] `customer.py` is under 1,200 lines
- [ ] `routes/devices.py` exists and is importable
- [ ] `routes/alerts.py` exists and is importable
- [ ] `routes/metrics.py` exists and is importable
- [ ] `routes/exports.py` exists and is importable
- [ ] All 4 new routers registered in `app.py`
- [ ] Route count before == route count after
- [ ] All smoke tests return HTTP 200
- [ ] Unit tests pass (same rate as before)
- [ ] No circular imports, no startup errors
