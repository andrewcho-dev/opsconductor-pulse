# Task 2: Configurable DB Pool Sizes

## Files to Modify

Every file that calls `asyncpg.create_pool()` with hard-coded `min_size`/`max_size`:

| File | Line(s) | Current |
|------|---------|---------|
| `services/ingest_iot/ingest.py` | 1040-1041, 1048-1049 | `min_size=2, max_size=10` |
| `services/evaluator_iot/evaluator.py` | 1201, 1205 | `min_size=2, max_size=10` |
| `services/ops_worker/main.py` | 50-51, 60-61 | `min_size=2, max_size=10` |
| `services/ops_worker/health_monitor.py` | 40, 45 | `min_size=2, max_size=10` |
| `services/ops_worker/metrics_collector.py` | 40, 45, 177, 182 | `min_size=2, max_size=10` |
| `services/ui_iot/app.py` | 526-527, 535-536 | `min_size=2, max_size=10` |
| `services/ui_iot/metrics_collector.py` | 41-46 | hard-coded |
| `services/ui_iot/routes/api_v2.py` | 37-40 | `min_size=1, max_size=5` |
| `services/ui_iot/routes/system.py` | 53-58 | hard-coded |
| `services/ui_iot/routes/operator.py` | 155-160 | hard-coded |

## What to Do

### Step 1: Add env var reads at module level in each service

In each service's main file (or a shared config module if one exists), add:

```python
PG_POOL_MIN = int(os.getenv("PG_POOL_MIN", "2"))
PG_POOL_MAX = int(os.getenv("PG_POOL_MAX", "10"))
```

The defaults match the current hard-coded values, so this is a zero-change deploy for existing environments.

### Step 2: Replace all hard-coded values

In every `asyncpg.create_pool()` call, replace:

```python
min_size=2,
max_size=10,
```

With:

```python
min_size=PG_POOL_MIN,
max_size=PG_POOL_MAX,
```

**Exception:** `services/ui_iot/routes/api_v2.py` currently uses `min_size=1, max_size=5` (smaller pool for the legacy v2 API). This is intentional — the v2 API is less critical and shouldn't compete for connections. Leave this one as-is, OR change it to use `PG_POOL_MIN` and `PG_POOL_MAX` with a note that it can be overridden.

### Step 3: For services with multiple pool creation sites

Some files (like `ops_worker/metrics_collector.py`) create pools in multiple places. They should all share the same env vars. If the env var is read at module level, all sites in the same process will use the same values.

For `ui_iot` sub-modules (`routes/api_v2.py`, `routes/system.py`, `routes/operator.py`, `metrics_collector.py`) — these run in the same process as `app.py`. Import `PG_POOL_MIN`/`PG_POOL_MAX` from `app.py` or read the env vars locally (simpler, avoids import coupling):

```python
_PG_POOL_MIN = int(os.getenv("PG_POOL_MIN", "2"))
_PG_POOL_MAX = int(os.getenv("PG_POOL_MAX", "10"))
```

### Step 4: Add env vars to docker-compose.yml

In `compose/docker-compose.yml`, add to each service's environment block (but only if we want to set non-default values). For now, just document the env vars — don't add them to docker-compose unless we're changing the defaults.

Add a comment in docker-compose.yml near the ingest service:

```yaml
    environment:
      # ... existing vars ...
      # PG_POOL_MIN: "2"      # DB pool minimum connections (default: 2)
      # PG_POOL_MAX: "10"     # DB pool maximum connections (default: 10)
```

## Important Notes

- This is a **safe, backward-compatible change** — defaults match current behavior
- The primary benefit is being able to tune pool sizes per service in production without code changes. For example:
  - Ingest may need `PG_POOL_MAX=20` under high load
  - Ops worker only needs `PG_POOL_MAX=5`
- PgBouncer is already configured with `MAX_CLIENT_CONN: 200` and `DEFAULT_POOL_SIZE: 20`, so individual services can be tuned up to that total limit
- Don't exceed PgBouncer's `DEFAULT_POOL_SIZE` across all services combined (currently 20 server-side connections shared by all services)

## Verification

```bash
# Check all pool creation sites use the env vars
grep -rn 'min_size=2\|max_size=10' services/ingest_iot/ services/evaluator_iot/ services/ops_worker/ services/ui_iot/
# Should return NO matches (all replaced with env var references)

# Check env vars are defined
grep -rn 'PG_POOL_MIN\|PG_POOL_MAX' services/
# Should show reads in each service
```
