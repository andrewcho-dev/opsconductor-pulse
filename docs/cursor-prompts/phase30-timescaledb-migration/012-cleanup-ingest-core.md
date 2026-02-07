# Phase 30.12: Clean Up Ingest Core Module

## Task

Remove obsolete InfluxDB line protocol helpers from `services/shared/ingest_core.py`. These functions are no longer used now that telemetry goes directly to TimescaleDB.

---

## Changes Required

### 1. Delete Line Protocol Functions

**Delete these functions (lines 29-75):**

```python
# DELETE ENTIRE FUNCTION (lines 29-31):
def _escape_tag_value(v: str) -> str:
    """Escape commas, equals, and spaces in InfluxDB line protocol tag values."""
    return v.replace("\\", "\\\\").replace(",", "\\,").replace("=", "\\=").replace(" ", "\\ ")


# DELETE ENTIRE FUNCTION (lines 34-36):
def _escape_field_key(key):
    """Escape field key for InfluxDB line protocol."""
    return str(key).replace("\\", "\\\\").replace(",", "\\,").replace("=", "\\=").replace(" ", "\\ ")


# DELETE ENTIRE FUNCTION (lines 39-75):
def _build_line_protocol(msg_type: str, device_id: str, site_id: str, payload: dict, event_ts) -> str:
    """Build InfluxDB line protocol string for a heartbeat or telemetry event."""
    escaped_device = _escape_tag_value(device_id)
    escaped_site = _escape_tag_value(site_id)

    if event_ts is not None:
        ns_ts = int(event_ts.timestamp() * 1_000_000_000)
    else:
        ns_ts = int(time.time() * 1_000_000_000)

    if msg_type == "heartbeat":
        seq = payload.get("seq", 0)
        return f"heartbeat,device_id={escaped_device},site_id={escaped_site} seq={seq}i {ns_ts}"

    elif msg_type == "telemetry":
        metrics = payload.get("metrics") or {}
        fields = []
        seq = payload.get("seq", 0)
        fields.append(f"seq={seq}i")

        for key, value in metrics.items():
            if value is None:
                continue
            escaped_key = _escape_field_key(key)
            if isinstance(value, bool):
                fields.append(f"{escaped_key}={'true' if value else 'false'}")
            elif isinstance(value, int):
                fields.append(f"{escaped_key}={value}i")
            elif isinstance(value, float):
                fields.append(f"{escaped_key}={value}")
            elif isinstance(value, str):
                continue

        field_str = ",".join(fields)
        return f"telemetry,device_id={escaped_device},site_id={escaped_site} {field_str} {ns_ts}"

    return ""
```

### 2. Update IngestResult Dataclass

**Remove the `line_protocol` field (line 302):**

Change from:
```python
@dataclass
class IngestResult:
    success: bool
    reason: str | None = None
    line_protocol: str | None = None
```

To:
```python
@dataclass
class IngestResult:
    success: bool
    reason: str | None = None
```

### 3. Update validate_and_prepare Function

**Remove line_protocol from the return statement (lines 375-377):**

Change from:
```python
    event_ts = parse_ts(payload.get("ts"))
    line_protocol = _build_line_protocol(msg_type, device_id, site_id, payload, event_ts)
    return IngestResult(True, line_protocol=line_protocol)
```

To:
```python
    return IngestResult(True)
```

---

## After Changes

The file should contain only:
1. `parse_ts()` - Timestamp parsing (still needed)
2. `sha256_hex()` - Token hashing (still needed)
3. `TokenBucket` - Rate limiting (still needed)
4. `DeviceAuthCache` - Credential caching (still needed)
5. `TelemetryRecord` - Data class for telemetry records (still needed)
6. `TimescaleBatchWriter` - Batched writes to TimescaleDB (still needed)
7. `IngestResult` - Validation result (simplified, no line_protocol)
8. `validate_and_prepare()` - Validation function (simplified)

---

## Verification

```bash
# Check Python syntax
cd /home/opsconductor/simcloud
python3 -m py_compile services/shared/ingest_core.py

# Restart ingest service
cd compose
docker compose restart ingest

# Verify ingestion still works
docker compose exec mqtt mosquitto_pub \
  -t "tenant/enabled/device/test-cleanup-001/telemetry" \
  -m '{"site_id":"lab-1","seq":1,"metrics":{"temp":25.5}}'

# Check logs
docker compose logs ingest --tail=10

# Verify data in TimescaleDB
docker compose exec postgres psql -U iot -d iotcloud -c "
SELECT time, tenant_id, device_id, metrics
FROM telemetry
WHERE device_id = 'test-cleanup-001'
ORDER BY time DESC LIMIT 1;
"
```

---

## Files

| Action | File |
|--------|------|
| MODIFY | `services/shared/ingest_core.py` |
