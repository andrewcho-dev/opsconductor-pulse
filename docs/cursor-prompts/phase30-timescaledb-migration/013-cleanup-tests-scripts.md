# Phase 30.13: Delete Obsolete InfluxDB Tests and Scripts

## Task

Remove test files and scripts that reference the now-removed InfluxDB functionality.

---

## Files to Delete

### 1. Test Files

**Delete these files entirely:**

```bash
# InfluxDB-specific test files
rm tests/unit/test_influxdb_helpers.py
rm tests/integration/test_influxdb_write.py
```

### 2. Scripts

**Delete this script:**

```bash
rm scripts/init_influxdb_tenants.py
```

---

## Files to Update

### 1. tests/unit/test_customer_route_handlers.py

**Remove InfluxDB mock references (around lines 617-618).**

Search for any lines like:
```python
# DELETE any lines containing:
influxdb
InfluxDB
INFLUXDB
influx_
```

### 2. tests/unit/test_operator_route_handlers.py

**Remove InfluxDB mock references (around lines 190-191).**

Search for any lines like:
```python
# DELETE any lines containing:
influxdb
InfluxDB
INFLUXDB
influx_
```

### 3. tests/unit/test_api_v2.py

**Remove InfluxDB references (around line 40).**

Search for any lines like:
```python
# DELETE any lines containing:
influxdb
InfluxDB
INFLUXDB
influx_
```

---

## Update Environment Files

### compose/.env

**Remove InfluxDB token:**

```bash
# DELETE this line:
INFLUXDB_TOKEN=influx-dev-token-change-me
```

### compose/.env.example (if it exists)

**Remove InfluxDB variables:**

```bash
# DELETE any lines containing:
INFLUXDB_TOKEN
INFLUXDB_URL
```

---

## Verification

```bash
# Check no InfluxDB references remain in test files
cd /home/opsconductor/simcloud
grep -r "influx" tests/ --include="*.py" | grep -v "__pycache__"

# Check scripts directory
ls scripts/ | grep -i influx

# Check .env file
grep -i influx compose/.env

# Run remaining tests to ensure nothing is broken
python3 -m pytest tests/unit/ -v --ignore=tests/unit/test_influxdb_helpers.py
```

---

## Files

| Action | File |
|--------|------|
| DELETE | `tests/unit/test_influxdb_helpers.py` |
| DELETE | `tests/integration/test_influxdb_write.py` |
| DELETE | `scripts/init_influxdb_tenants.py` |
| MODIFY | `tests/unit/test_customer_route_handlers.py` |
| MODIFY | `tests/unit/test_operator_route_handlers.py` |
| MODIFY | `tests/unit/test_api_v2.py` |
| MODIFY | `compose/.env` |
