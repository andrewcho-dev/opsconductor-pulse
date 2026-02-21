# Task 3: Convert `os.environ[]` to `os.getenv()` With Defaults

## Context

13 module-level `os.environ["KEY"]` calls cause `KeyError` when environment variables aren't set, preventing test collection. Convert each to `os.getenv("KEY", default)`.

## Changes

Make each substitution exactly as shown. The pattern is:
`os.environ["KEY"]` → `os.getenv("KEY", "default")`

### File 1: `services/ui_iot/services/keycloak_admin.py` line 22

```python
# BEFORE:
KEYCLOAK_ADMIN_PASSWORD = os.environ["KEYCLOAK_ADMIN_PASSWORD"]

# AFTER:
KEYCLOAK_ADMIN_PASSWORD = os.getenv("KEYCLOAK_ADMIN_PASSWORD", "")
```

### File 2: `services/ui_iot/app.py` line 120

```python
# BEFORE:
PG_PASS = os.environ["PG_PASS"]

# AFTER:
PG_PASS = os.getenv("PG_PASS", "iot_dev")
```

### File 3: `services/ui_iot/metrics_collector.py` line 21

```python
# BEFORE:
PG_PASS = os.environ["PG_PASS"]

# AFTER:
PG_PASS = os.getenv("PG_PASS", "iot_dev")
```

### File 4: `services/ui_iot/routes/api_v2.py` line 24

```python
# BEFORE:
PG_PASS = os.environ["PG_PASS"]

# AFTER:
PG_PASS = os.getenv("PG_PASS", "iot_dev")
```

### File 5: `services/ui_iot/routes/operator.py` line 43

```python
# BEFORE:
PG_PASS = os.environ["PG_PASS"]

# AFTER:
PG_PASS = os.getenv("PG_PASS", "iot_dev")
```

### File 6: `services/ui_iot/routes/system.py` line 24

**Note:** Variable name here is `POSTGRES_PASS`, not `PG_PASS`.

```python
# BEFORE:
POSTGRES_PASS = os.environ["PG_PASS"]

# AFTER:
POSTGRES_PASS = os.getenv("PG_PASS", "iot_dev")
```

### File 7: `services/evaluator_iot/evaluator.py` line 47

```python
# BEFORE:
PG_PASS = os.environ["PG_PASS"]

# AFTER:
PG_PASS = os.getenv("PG_PASS", "iot_dev")
```

### File 8: `services/ingest_iot/ingest.py` line 43

```python
# BEFORE:
PG_PASS = os.environ["PG_PASS"]

# AFTER:
PG_PASS = os.getenv("PG_PASS", "iot_dev")
```

### File 9: `services/ops_worker/main.py` line 33

```python
# BEFORE:
PG_PASS = os.environ["PG_PASS"]

# AFTER:
PG_PASS = os.getenv("PG_PASS", "iot_dev")
```

### File 10: `services/ops_worker/health_monitor.py` line 18

```python
# BEFORE:
PG_PASS = os.environ["PG_PASS"]

# AFTER:
PG_PASS = os.getenv("PG_PASS", "iot_dev")
```

### File 11: `services/ops_worker/metrics_collector.py` line 20

```python
# BEFORE:
PG_PASS = os.environ["PG_PASS"]

# AFTER:
PG_PASS = os.getenv("PG_PASS", "iot_dev")
```

### File 12: `services/subscription_worker/worker.py` line 39

```python
# BEFORE:
DATABASE_URL = os.environ["DATABASE_URL"]

# AFTER:
DATABASE_URL = os.getenv("DATABASE_URL", "")
```

### File 13: `services/provision_api/app.py` lines 23 AND 26

Two changes in the same file:

```python
# Line 23 BEFORE:
PG_PASS = os.environ["PG_PASS"]
# Line 23 AFTER:
PG_PASS = os.getenv("PG_PASS", "iot_dev")

# Line 26 BEFORE:
ADMIN_KEY = os.environ["ADMIN_KEY"]
# Line 26 AFTER:
ADMIN_KEY = os.getenv("ADMIN_KEY", "")
```

## Safety

- All production/compose deployments set these vars explicitly via `.env` or compose environment blocks
- The defaults match the existing `tests/conftest.py` test defaults
- Empty strings for passwords/keys mean auth will fail at runtime (not silently succeed)
- No behavioral change in production — only prevents import-time crashes when vars are unset
