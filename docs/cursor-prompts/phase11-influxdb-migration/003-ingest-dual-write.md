# Task 003: Ingest Dual-Write

> **CURSOR: EXECUTE THIS TASK**
>
> Read the instructions below and implement them exactly.
> This task adds InfluxDB line protocol writing to the ingest service alongside the existing PostgreSQL writes.
> Both databases receive every accepted event during this dual-write phase.
> RUN THE TESTS in the Test section. Do not proceed if tests fail.

---

## Context

Currently, accepted events flow:
```
MQTT → db_worker() → _insert_raw() → PostgreSQL raw_events table
```

After this task:
```
MQTT → db_worker() → _insert_raw() → PostgreSQL raw_events table
                    → _write_influxdb() → InfluxDB telemetry_{tenant_id}
```

The InfluxDB write is best-effort during dual-write phase — failures are counted but don't block processing.

**Read first**:
- `services/ingest_iot/ingest.py` (full file — understand db_worker flow, _insert_raw, stats_worker)
- `services/ingest_iot/requirements.txt`
- `simulator/device_sim_iot/sim.py` lines 79-132 (payload shapes for heartbeat and telemetry)

**Key payload shapes from simulator**:
- **Heartbeat**: `{ts, tenant_id, site_id, device_id, msg_type:"heartbeat", seq, provision_token}`
- **Telemetry**: same + `metrics: {battery_pct: float, temp_c: float, rssi_dbm: int, snr_db: float, uplink_ok: bool}`

**Target InfluxDB line protocol**:
```
heartbeat,device_id=dev-0001,site_id=lab-1 seq=120i <ns_epoch>
telemetry,device_id=dev-0001,site_id=lab-1 battery_pct=87.5,temp_c=24.3,rssi_dbm=-85i,snr_db=12.4,uplink_ok=true,seq=120i <ns_epoch>
```

---

## Task

### 3.1 Add httpx to ingest requirements

In `services/ingest_iot/requirements.txt`, add:
```
httpx==0.27.0
```

### 3.2 Add imports and env vars

At the top of `services/ingest_iot/ingest.py`, add `import httpx` after the existing imports (after line 9).

After line 26 (`LOG_STATS_EVERY_SECONDS`), add:
```python
INFLUXDB_URL = os.getenv("INFLUXDB_URL", "http://iot-influxdb:8181")
INFLUXDB_TOKEN = os.getenv("INFLUXDB_TOKEN", "influx-dev-token-change-me")
INFLUXDB_WRITE_ENABLED = os.getenv("INFLUXDB_WRITE_ENABLED", "1") == "1"
```

### 3.3 Add line protocol helper functions

After the `sha256_hex` function (after line 40), add these helpers:

```python
def _escape_tag_value(v: str) -> str:
    """Escape commas, equals, and spaces in InfluxDB line protocol tag values."""
    return v.replace("\\", "\\\\").replace(",", "\\,").replace("=", "\\=").replace(" ", "\\ ")


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

        if metrics.get("battery_pct") is not None:
            fields.append(f"battery_pct={metrics['battery_pct']}")
        if metrics.get("temp_c") is not None:
            fields.append(f"temp_c={metrics['temp_c']}")
        if metrics.get("rssi_dbm") is not None:
            fields.append(f"rssi_dbm={metrics['rssi_dbm']}i")
        if metrics.get("snr_db") is not None:
            fields.append(f"snr_db={metrics['snr_db']}")
        if metrics.get("uplink_ok") is not None:
            fields.append(f"uplink_ok={str(metrics['uplink_ok']).lower()}")

        if not fields:
            return ""

        field_str = ",".join(fields)
        return f"telemetry,device_id={escaped_device},site_id={escaped_site} {field_str} {ns_ts}"

    return ""
```

### 3.4 Add InfluxDB client to Ingestor.__init__

In the `Ingestor.__init__` method (after line 149, after `self.buckets`), add:
```python
        self.influx_client: httpx.AsyncClient | None = None
        self.influx_ok = 0
        self.influx_err = 0
```

### 3.5 Create httpx client in Ingestor.run()

In `Ingestor.run()`, after `await self.init_db()` (after line 421), add:
```python
        if INFLUXDB_WRITE_ENABLED:
            self.influx_client = httpx.AsyncClient(timeout=10.0)
```

### 3.6 Add _write_influxdb method

Add this method to the `Ingestor` class (after `_insert_raw`, around line 297):

```python
    async def _write_influxdb(self, tenant_id, device_id, site_id, msg_type, payload, event_ts):
        """Write event to InfluxDB. Best-effort: failures are counted but don't raise."""
        if not INFLUXDB_WRITE_ENABLED or self.influx_client is None:
            return

        line = _build_line_protocol(msg_type, device_id, site_id, payload, event_ts)
        if not line:
            return

        db_name = f"telemetry_{tenant_id}"
        try:
            resp = await self.influx_client.post(
                f"{INFLUXDB_URL}/api/v3/write_lp?db={db_name}",
                content=line,
                headers={
                    "Authorization": f"Bearer {INFLUXDB_TOKEN}",
                    "Content-Type": "text/plain",
                },
            )
            if resp.status_code < 300:
                self.influx_ok += 1
            else:
                self.influx_err += 1
        except Exception:
            self.influx_err += 1
```

### 3.7 Call _write_influxdb from db_worker

In `db_worker`, after the `await self._insert_raw(...)` call (line 382), add:

```python
                await self._write_influxdb(tenant_id, device_id, site_id, msg_type, payload, event_ts)
```

**Important**: This line goes INSIDE the try block, at the same indentation as `_insert_raw`. It must be after the PG write but before the `except` block.

### 3.8 Add InfluxDB stats to stats_worker

In `stats_worker` (line 220-224), modify the print statement to append InfluxDB counters. Change:

```python
            print(
                f"[stats] received={self.msg_received} enqueued={self.msg_enqueued} dropped={self.msg_dropped} "
                f"qsize={self.queue.qsize()} mode={self.mode} store_rejects={int(self.store_rejects)} mirror_rejects={int(self.mirror_rejects)} "
                f"max_payload_bytes={self.max_payload_bytes} rps={self.rps} burst={self.burst}"
            )
```

To:

```python
            print(
                f"[stats] received={self.msg_received} enqueued={self.msg_enqueued} dropped={self.msg_dropped} "
                f"qsize={self.queue.qsize()} mode={self.mode} store_rejects={int(self.store_rejects)} mirror_rejects={int(self.mirror_rejects)} "
                f"max_payload_bytes={self.max_payload_bytes} rps={self.rps} burst={self.burst} "
                f"influx_ok={self.influx_ok} influx_err={self.influx_err}"
            )
```

---

## Files to Create/Modify

| Action | Path |
|--------|------|
| MODIFY | `services/ingest_iot/ingest.py` |
| MODIFY | `services/ingest_iot/requirements.txt` |

---

## Test

```bash
# 1. Rebuild and restart ingest
cd compose && docker compose up -d --build ingest

# 2. Wait for the simulator to send some data (30 seconds)
sleep 30

# 3. Check ingest logs for influx stats
docker logs iot-ingest --tail 5
# Should see: influx_ok=N influx_err=0 (N > 0)

# 4. Query InfluxDB for telemetry data
curl -s -X POST http://localhost:8181/api/v3/query_sql \
  -H "Authorization: Bearer influx-dev-token-change-me" \
  -H "Content-Type: application/json" \
  -d '{"db":"telemetry_enabled","q":"SELECT COUNT(*) AS cnt FROM telemetry"}'
# Expect count > 0

# 5. Query InfluxDB for heartbeat data
curl -s -X POST http://localhost:8181/api/v3/query_sql \
  -H "Authorization: Bearer influx-dev-token-change-me" \
  -H "Content-Type: application/json" \
  -d '{"db":"telemetry_enabled","q":"SELECT COUNT(*) AS cnt FROM heartbeat"}'
# Expect count > 0

# 6. Verify PG still has new rows (dual-write working)
docker exec iot-postgres psql -U iot -d iotcloud -c \
  "SELECT COUNT(*) FROM raw_events WHERE ingested_at > now() - interval '1 minute'"
# Expect count > 0

# 7. Run unit tests
cd /home/opsconductor/simcloud
python -m pytest tests/unit/ -v -x
```

---

## Acceptance Criteria

- [ ] `httpx==0.27.0` is in `services/ingest_iot/requirements.txt`
- [ ] `_escape_tag_value()` correctly escapes commas, equals, and spaces
- [ ] `_build_line_protocol()` generates correct line protocol for heartbeat and telemetry
- [ ] `_build_line_protocol()` skips None metric fields (doesn't include them in output)
- [ ] `_build_line_protocol()` uses nanosecond epoch timestamps
- [ ] `Ingestor._write_influxdb()` writes to `telemetry_{tenant_id}` database
- [ ] InfluxDB write failures are counted but do not block processing
- [ ] `stats_worker` prints `influx_ok` and `influx_err` counters
- [ ] Both PostgreSQL and InfluxDB receive accepted events (dual-write)
- [ ] `INFLUXDB_WRITE_ENABLED=0` disables InfluxDB writes
- [ ] All existing unit tests still pass

---

## Commit

```
Add InfluxDB dual-write to ingest service

- Add line protocol helpers (_escape_tag_value, _build_line_protocol)
- Write heartbeat and telemetry events to InfluxDB alongside PostgreSQL
- Best-effort InfluxDB writes with ok/err counters in stats
- Feature flag INFLUXDB_WRITE_ENABLED (default on)
- Add httpx to ingest dependencies

Part of Phase 11: InfluxDB Telemetry Migration
```
