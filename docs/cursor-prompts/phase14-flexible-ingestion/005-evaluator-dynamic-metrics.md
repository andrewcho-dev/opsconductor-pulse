# Task 005: Evaluator Dynamic Metrics

> **CURSOR: EXECUTE THIS TASK**
>
> Read the instructions below and implement them exactly.
> Modify only the files listed in "Files to Modify".
> RUN THE TESTS in the Test section. Do not proceed if tests fail.
> IMPORTANT: Do not commit until all tests pass.

---

## Context

**THE PROBLEM**: The evaluator queries InfluxDB with hardcoded field names in two places:

1. **Metrics query** (lines 205-209 of evaluator.py):
```sql
SELECT device_id, battery_pct, temp_c, rssi_dbm, snr_db, uplink_ok, time
FROM telemetry WHERE time > now() - INTERVAL '30 minutes'
ORDER BY time DESC
```

2. **State blob construction** (lines 280-286 of evaluator.py):
```python
state_blob = {
    "battery_pct": r["battery_pct"],
    "temp_c": r["temp_c"],
    "rssi_dbm": r["rssi_dbm"],
    "snr_db": r["snr_db"],
    "uplink_ok": r["uplink_ok"],
}
```

After Task 002, devices can send arbitrary metrics (pressure_psi, flow_rate, etc.). The evaluator needs to discover and store whatever fields exist, not just the five hardcoded ones.

**Read first**:
- `services/evaluator_iot/evaluator.py` — focus on:
  - `fetch_rollup_influxdb` function (lines 152-250)
  - The metrics query (lines 205-209)
  - The state_blob construction (lines 280-286)
  - The `results.append` block (lines 235-248)

---

## Task

### 5.1 Change metrics query to SELECT *

**File**: `services/evaluator_iot/evaluator.py`

Find the telemetry metrics query at lines 205-209:
```python
metrics_rows = await _influx_query(
    http_client, db_name,
    "SELECT device_id, battery_pct, temp_c, rssi_dbm, snr_db, uplink_ok, time "
    "FROM telemetry WHERE time > now() - INTERVAL '30 minutes' "
    "ORDER BY time DESC"
)
```

Replace the SQL string with:
```python
"SELECT * FROM telemetry WHERE time > now() - INTERVAL '30 minutes' "
"ORDER BY time DESC"
```

The heartbeat query (lines 181-185) and telemetry MAX(time) query (lines 193-197) do NOT need to change — they only reference `device_id` and `time`, which are always present.

### 5.2 Dynamically build state JSONB from metrics_map

**File**: `services/evaluator_iot/evaluator.py`

Find the `results.append` block (lines 235-248) where individual metric fields are extracted. Currently lines 235-248 look like:

```python
results.append({
    "tenant_id": d["tenant_id"],
    "device_id": did,
    "site_id": d["site_id"],
    "registry_status": d["status"],
    "last_hb": last_hb,
    "last_tel": last_tel,
    "last_seen": last_seen,
    "battery_pct": m.get("battery_pct"),
    "temp_c": m.get("temp_c"),
    "rssi_dbm": m.get("rssi_dbm"),
    "snr_db": m.get("snr_db"),
    "uplink_ok": m.get("uplink_ok"),
})
```

Replace this with a dynamic approach. Build a `metrics` dict from whatever keys are in `m`, excluding metadata keys:

```python
# Build metrics dict from all available fields, excluding metadata
EXCLUDE_KEYS = {"time", "device_id", "site_id", "seq"}
device_metrics = {}
for key, value in m.items():
    if key in EXCLUDE_KEYS:
        continue
    if key.startswith("iox::"):  # InfluxDB internal columns
        continue
    if value is not None:
        device_metrics[key] = value

results.append({
    "tenant_id": d["tenant_id"],
    "device_id": did,
    "site_id": d["site_id"],
    "registry_status": d["status"],
    "last_hb": last_hb,
    "last_tel": last_tel,
    "last_seen": last_seen,
    "metrics": device_metrics,
})
```

### 5.3 Update state_blob construction in main loop

**File**: `services/evaluator_iot/evaluator.py`

Find the state_blob construction in the main loop (lines 280-287):
```python
state_blob = {
    "battery_pct": r["battery_pct"],
    "temp_c": r["temp_c"],
    "rssi_dbm": r["rssi_dbm"],
    "snr_db": r["snr_db"],
    "uplink_ok": r["uplink_ok"],
}
state_blob = {k: v for k, v in state_blob.items() if v is not None}
```

Replace with:
```python
state_blob = r.get("metrics", {})
```

This uses the dynamically-built metrics dict from step 5.2 directly. The `metrics` dict already excludes None values and metadata keys.

### 5.4 Verify deduplication logic

**File**: `services/evaluator_iot/evaluator.py`

The deduplication at lines 212-216 keeps only the latest row per device_id:
```python
metrics_map: dict[str, dict] = {}
for row in metrics_rows:
    did = row.get("device_id")
    if did and did not in metrics_map:
        metrics_map[did] = row
```

This works unchanged because it's based on `device_id` (always present) and the ORDER BY time DESC ensures the first row per device is the latest. No changes needed here — just verify it still works.

### 5.5 Verify fetch_rollup_influxdb return format

The function `fetch_rollup_influxdb` has a docstring (lines 152-157) that lists the expected return keys including `battery_pct`, `temp_c`, etc. Update the docstring to reflect the new dynamic format:

```python
"""Fetch device rollup data from InfluxDB + PG device_registry.

Returns list of dicts with keys:
tenant_id, device_id, site_id, registry_status, last_hb, last_tel,
last_seen, metrics (dict of all available metric fields)
"""
```

---

## Files to Modify

| Action | Path | What changes |
|--------|------|--------------|
| MODIFY | `services/evaluator_iot/evaluator.py` | SELECT * query, dynamic metrics dict, dynamic state_blob, updated docstring |

---

## Test

### Step 1: Run existing unit tests

```bash
cd /home/opsconductor/simcloud && python3 -m pytest tests/unit/ -v -x
```

If any evaluator-related tests reference specific hardcoded fields like `r["battery_pct"]`, they need to be updated to use `r["metrics"]["battery_pct"]` or `r.get("metrics", {}).get("battery_pct")`.

### Step 2: Verify evaluator handles dynamic fields

Read the code and confirm:
- [ ] Metrics query uses `SELECT *` (not hardcoded fields)
- [ ] `results.append` builds a `metrics` dict dynamically from row keys
- [ ] Internal keys (`time`, `device_id`, `site_id`, `seq`, `iox::*`) excluded from metrics
- [ ] `state_blob` uses the dynamic metrics dict
- [ ] NO_HEARTBEAT alert logic unchanged (lines 311-321)
- [ ] Heartbeat MAX(time) query unchanged (lines 181-185)
- [ ] Telemetry MAX(time) query unchanged (lines 193-197)

---

## Acceptance Criteria

- [ ] Evaluator discovers and stores arbitrary metric fields from InfluxDB
- [ ] State JSONB contains whatever metrics the device sends
- [ ] No hardcoded field names in the metrics query
- [ ] Return format uses `metrics` dict instead of individual field keys
- [ ] NO_HEARTBEAT alert generation unchanged
- [ ] Heartbeat tracking unchanged
- [ ] Docstring updated
- [ ] All existing unit tests pass

---

## Commit

```
Update evaluator to handle arbitrary device metrics

Change InfluxDB telemetry query from hardcoded field list to
SELECT *. Build device_state JSONB dynamically from whatever
metric fields are available. Prepares for custom alert rules.

Phase 14 Task 5: Evaluator Dynamic Metrics
```
