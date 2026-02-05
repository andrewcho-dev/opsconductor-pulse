# Task 002: Flexible Telemetry Schema — Accept Arbitrary Device Metrics

> **CURSOR: EXECUTE THIS TASK**
>
> Read the instructions below and implement them exactly.
> Modify only the files listed in "Files to Modify".
> RUN THE TESTS in the Test section. Do not proceed if tests fail.
> IMPORTANT: Do not commit until all tests pass.

---

## Context

**THE PROBLEM**: The ingest pipeline hardcodes five telemetry fields: `battery_pct`, `temp_c`, `rssi_dbm`, `snr_db`, `uplink_ok`. If a device sends `pressure_psi`, `flow_rate`, or `vibration_g`, they are silently ignored. The `_build_line_protocol` function (lines 50-87 in ingest.py) extracts these specific fields from the payload's `metrics` dict and builds InfluxDB line protocol with only those fields.

We need the ingest pipeline to accept ANY numeric or boolean metric key in the `metrics` dict and write all of them to InfluxDB. InfluxDB is schemaless — it handles new fields automatically.

**Read first**:
- `services/ingest_iot/ingest.py` — focus on `_build_line_protocol` function (lines 50-87) and `_escape_tag_value` (line 45)

---

## Task

### 2.1 Add `_escape_field_key` helper

**File**: `services/ingest_iot/ingest.py`

Add a helper function right after `_escape_tag_value` (after line 47):

```python
def _escape_field_key(key):
    """Escape field key for InfluxDB line protocol."""
    return str(key).replace("\\", "\\\\").replace(",", "\\,").replace("=", "\\=").replace(" ", "\\ ")
```

### 2.2 Rewrite `_build_line_protocol` for dynamic fields

**File**: `services/ingest_iot/ingest.py`

Replace the `_build_line_protocol` function (lines 50-87). The new implementation must:

**Heartbeat messages** (msg_type == "heartbeat"):
- Keep the existing format exactly unchanged. Heartbeats are simple:
  ```
  heartbeat,device_id={escaped},site_id={escaped} seq={seq}i {ns_ts}
  ```
- Extract `seq` from `payload.get("seq", 0)`

**Telemetry messages** (msg_type == "telemetry"):
- Tags: `device_id={escaped},site_id={escaped}` (same as now)
- Fields: Start with `seq={seq}i` where `seq = payload.get("seq", 0)`
- Then iterate over `metrics = payload.get("metrics") or {}`. For each key-value pair:
  - If value is `bool` (CHECK BOOL BEFORE INT — `isinstance(value, bool)` must come before `isinstance(value, int)` because `bool` is a subclass of `int` in Python): format as `{escaped_key}=true` or `{escaped_key}=false` (lowercase)
  - If value is `int`: format as `{escaped_key}={value}i`
  - If value is `float`: format as `{escaped_key}={value}`
  - If value is `str`: **skip it** (do not include string fields — high-cardinality strings degrade InfluxDB)
  - If value is `None`: **skip it**
  - Use `_escape_field_key(key)` for field key escaping
- Join all field pairs with commas (seq first, then the metric fields)
- If the metrics dict is empty or None, still write the line with just `seq`
- Timestamp: nanosecond precision (same as current implementation)
- Return empty string for unknown msg_type (same as current)

**Important**: The existing payload format with `battery_pct`, `temp_c`, etc. still works because those are just regular keys in the `metrics` dict. No special handling needed — they flow through the generic iterator. The key difference: `rssi_dbm` is an `int` and will now consistently get the `i` suffix (previously it was hardcoded with `i`), `battery_pct`/`temp_c`/`snr_db` are floats (no suffix), and `uplink_ok` is a bool (lowercase true/false). This matches the existing behavior.

### 2.3 Verify payload validation in db_worker

**File**: `services/ingest_iot/ingest.py`

Read through `db_worker` and confirm that it does NOT validate specific metric fields inside the `metrics` dict. The current code (lines 339-433) doesn't extract or validate individual metrics — it passes the whole payload to `_write_influxdb` which calls `_build_line_protocol`. So no changes should be needed here. If for some reason there IS validation of specific metric keys, remove it. The `metrics` field should be accepted as any dict (or absent/null).

---

## Files to Modify

| Action | Path | What changes |
|--------|------|--------------|
| MODIFY | `services/ingest_iot/ingest.py` | Add `_escape_field_key`, rewrite `_build_line_protocol` for dynamic fields |

---

## Test

### Step 1: Run existing unit tests

```bash
cd /home/opsconductor/simcloud && python3 -m pytest tests/unit/ -v -x
```

All existing tests must pass. If any test depends on the exact line protocol format with hardcoded fields, update that test to match the new dynamic format.

### Step 2: Verify line protocol handles various types

After making changes, mentally trace through these payloads and confirm the output:

**Existing format** (must still work):
```json
{"metrics": {"battery_pct": 87.5, "temp_c": 24.2, "rssi_dbm": -95, "snr_db": 8.5, "uplink_ok": true}, "seq": 5}
```
Expected line protocol fields should include: `seq=5i,battery_pct=87.5,temp_c=24.2,rssi_dbm=-95i,snr_db=8.5,uplink_ok=true` (order of metric fields may vary since dict iteration order is insertion order, but seq must be first)

**New arbitrary metrics**:
```json
{"metrics": {"pressure_psi": 42.7, "flow_rate": 120, "valve_open": true}}
```
Expected fields: `seq=0i,pressure_psi=42.7,flow_rate=120i,valve_open=true`

**Mixed with strings (strings dropped)**:
```json
{"metrics": {"temp_c": 55.0, "location": "building-A"}}
```
Expected fields: `seq=0i,temp_c=55.0` (location dropped)

**Empty metrics**:
```json
{"metrics": {}}
```
Expected fields: `seq=0i`

---

## Acceptance Criteria

- [ ] `_escape_field_key` function added
- [ ] `_build_line_protocol` accepts arbitrary numeric/boolean metrics
- [ ] Integer values get `i` suffix in line protocol
- [ ] Float values have no suffix
- [ ] Boolean values are lowercase `true`/`false` (bool checked BEFORE int)
- [ ] String values are silently dropped
- [ ] None values are silently dropped
- [ ] Heartbeat format unchanged
- [ ] Existing payload format (battery_pct, temp_c, etc.) still works identically
- [ ] Field keys are properly escaped via `_escape_field_key`
- [ ] All existing unit tests pass

---

## Commit

```
Accept arbitrary device metrics in telemetry ingestion

Rewrite _build_line_protocol to iterate over the metrics dict
dynamically instead of hardcoding five specific fields. Any numeric
or boolean value is written to InfluxDB. String values are dropped
to avoid high-cardinality field issues.

Phase 14 Task 2: Flexible Telemetry Schema
```
