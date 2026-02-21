# Phase 116 — Fix subscription-worker (Complete)

## Problem 1 (FIXED): Missing httpx
Duplicate `FROM` in Dockerfile. Fixed by removing duplicate and using
`requirements.txt`.

## Problem 2 (FIXED): Missing email_templates.py and shared/
Build context was `../services/subscription_worker` (too narrow).
Fixed by widening to `../services` and copying `shared/` + `*.py`.

## Problem 3: Stale import — `configure_root_logger` does not exist

`worker.py` line 34 imports `configure_root_logger` from `shared.log`.
That function does not exist. The actual function is `configure_logging`
in `shared/logging.py`. Every other service uses `shared.logging`.

### File to Modify

`services/subscription_worker/worker.py`

### Change

**Find (lines 34-37):**
```python
from shared.log import configure_root_logger, get_logger

configure_root_logger()
logger = get_logger(__name__)
```

**Replace with:**
```python
from shared.logging import configure_logging, get_logger

configure_logging("subscription_worker")
logger = get_logger(__name__)
```

### Also Fix (if desired): services/maintenance/log_cleanup.py

Same stale import exists at lines 13-15. Apply the same change:
```python
from shared.logging import configure_logging, get_logger
configure_logging("log_cleanup")
```

### Rebuild and Verify

```bash
cd ~/simcloud/compose
docker compose build subscription-worker
docker compose up -d subscription-worker
sleep 10
docker compose logs subscription-worker --tail=20
# Expected: JSON-formatted logs, "Starting subscription worker run...",
#           then "Sleeping for 3600 seconds..."
docker compose ps | grep subscription
# Expected: Up (healthy), NOT "Restarting"
```
