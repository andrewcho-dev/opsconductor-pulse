# Phase 110 — Fix Hardcoded Values in Application Code

## Fix 1: maintenance/log_cleanup.py — hardcoded DB URL

### Find the file
```bash
grep -n "localhost\|iot_dev\|postgresql://" services/maintenance/log_cleanup.py | head -10
```

### Fix

The file has a hardcoded fallback:
```python
"postgresql://iot:iot_dev@localhost:5432/iotcloud"
```

Replace with:
```python
import os
DATABASE_URL = os.environ["DATABASE_URL"]
```

Remove the hardcoded default entirely. If `DATABASE_URL` is not set, the
service should fail at startup with a clear error — not silently connect
to the wrong database.

Also replace `logging.basicConfig(level=logging.INFO)` with the shared
JSON logger:
```python
from shared.log import configure_root_logger, get_logger
configure_root_logger()
logger = get_logger(__name__)
```

---

## Fix 2: subscription_worker — wrong PgBouncer hostname

### Find the file
```bash
grep -n "postgres\|DATABASE_URL\|pgbouncer" services/subscription_worker/worker.py | head -10
```

The worker connects directly to `postgres:5432` (the old container name)
instead of `iot-pgbouncer:5432`.

### Fix

Replace the DB connection string or env var reference to use:
```python
DATABASE_URL = os.environ["DATABASE_URL"]
```

where `DATABASE_URL` in the compose env is already set to
`postgresql://iot:${PG_PASS}@iot-pgbouncer:5432/iotcloud`.

This ensures the subscription worker goes through PgBouncer like all other services.

Also replace `logging.basicConfig(level=logging.INFO)` with:
```python
from shared.log import configure_root_logger, get_logger
configure_root_logger()
logger = get_logger(__name__)
```

---

## Fix 3: Remove legacy Dockerfiles

Three Dockerfiles exist but are not referenced in docker-compose.yml:
- `services/ingest/Dockerfile`
- `services/evaluator/Dockerfile`
- `simulator/device_sim/Dockerfile`

Verify they are truly orphaned:
```bash
grep -r "services/ingest/Dockerfile\|services/evaluator/Dockerfile\|device_sim/Dockerfile" \
  compose/ Makefile 2>/dev/null
```

If no references found, delete them:
```bash
rm services/ingest/Dockerfile
rm services/evaluator/Dockerfile
rm simulator/device_sim/Dockerfile
```

If `services/ingest/` or `services/evaluator/` directories are now empty,
delete them too — they shadow the active `services/ingest_iot/` and
`services/evaluator_iot/` directories and will cause confusion.

---

## Fix 4: Verify no remaining hardcoded credentials in Python source

```bash
grep -rn "iot_dev\|change-me-now\|admin_dev\|192\.168\." \
  services/ --include="*.py" | grep -v "__pycache__"
```

For any matches found:
- If it's a test file using a dev credential → acceptable, leave it
- If it's production application code with a hardcoded credential → replace
  with `os.environ["VAR_NAME"]` (no default)
