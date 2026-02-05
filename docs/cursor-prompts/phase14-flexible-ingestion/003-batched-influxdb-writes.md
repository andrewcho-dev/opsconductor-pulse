# Task 003: Batched InfluxDB Writes

> **CURSOR: EXECUTE THIS TASK**
>
> Read the instructions below and implement them exactly.
> Modify only the files listed in "Files to Modify".
> RUN THE TESTS in the Test section. Do not proceed if tests fail.
> IMPORTANT: Do not commit until all tests pass.

---

## Context

**THE PROBLEM**: The `_write_influxdb` method (lines 310-337) does one HTTP POST per MQTT message. Each write goes to `/api/v3/write_lp?db=telemetry_{tenant_id}`. At 500 msg/sec, that is 500 HTTP round-trips per second to InfluxDB. InfluxDB performs much better with batched writes — one POST containing hundreds of line protocol lines.

**Read first**:
- `services/ingest_iot/ingest.py` — focus on `_write_influxdb` method (lines 310-337) and where it is called in `db_worker` (line 423)

---

## Task

### 3.1 Add environment variables

**File**: `services/ingest_iot/ingest.py`

Add near the other env vars (after `AUTH_CACHE_MAX_SIZE` from Task 001):

```python
INFLUX_BATCH_SIZE = int(os.getenv("INFLUX_BATCH_SIZE", "500"))
INFLUX_FLUSH_INTERVAL_MS = int(os.getenv("INFLUX_FLUSH_INTERVAL_MS", "1000"))
```

### 3.2 Add InfluxBatchWriter class

**File**: `services/ingest_iot/ingest.py`

Add a new class `InfluxBatchWriter` after the `DeviceAuthCache` class (from Task 001) and before the `Ingestor` class.

**Constructor** `__init__(self, http_client, influx_url, influx_token, batch_size=500, flush_interval_ms=1000)`:
- Store all parameters as instance vars: `self._http = http_client`, `self._influx_url = influx_url`, `self._influx_token = influx_token`, `self._batch_size = batch_size`, `self._flush_interval_ms = flush_interval_ms`
- `self._buffers = {}` — dict mapping `tenant_id` -> list of line protocol strings
- `self._flush_task = None` — will hold the asyncio periodic flush task
- Counters: `self.writes_ok = 0`, `self.writes_err = 0`, `self.flushes = 0`

**`async def start(self)`**:
- Start the periodic flush background task: `self._flush_task = asyncio.create_task(self._periodic_flush())`

**`async def stop(self)`**:
- Cancel the periodic flush task if it exists
- Await cancellation with try/except CancelledError
- Call `await self.flush_all()` to drain remaining buffers

**`async def add(self, tenant_id, line)`**:
- Append `line` to `self._buffers.setdefault(tenant_id, [])`
- Check if `len(self._buffers[tenant_id]) >= self._batch_size`
- If so, pop that tenant's buffer (replace with empty list), and call `await self._write_batch(tenant_id, lines)` with the popped lines

**`async def _periodic_flush(self)`**:
- Loop forever: `await asyncio.sleep(self._flush_interval_ms / 1000.0)`, then `await self.flush_all()`
- Wrap entire loop body in try/except asyncio.CancelledError: break out of loop
- Also wrap the sleep+flush in a generic try/except Exception to log and continue (don't crash the flush loop)

**`async def flush_all(self)`**:
- Snapshot and clear all buffers: `to_flush = self._buffers` then `self._buffers = {}`
- For each `(tenant_id, lines)` in `to_flush.items()` where `lines` is non-empty: call `await self._write_batch(tenant_id, lines)`

**`async def _write_batch(self, tenant_id, lines)`**:
- Build the database name: `f"telemetry_{tenant_id}"`
- Join all lines with `\n`: `body = "\n".join(lines)`
- Headers: `{"Authorization": f"Bearer {self._influx_token}", "Content-Type": "text/plain"}`
- Retry loop (2 attempts, same pattern as existing `_write_influxdb`):
  - `resp = await self._http.post(f"{self._influx_url}/api/v3/write_lp?db={db_name}", content=body, headers=headers)`
  - If `resp.status_code < 300`: `self.writes_ok += len(lines)`, `self.flushes += 1`, return
  - Else: print warning with status code and response text
- On complete failure (both attempts failed): `self.writes_err += len(lines)`, log error

**`def stats(self)`**: Return dict with:
- `"writes_ok"`: self.writes_ok
- `"writes_err"`: self.writes_err
- `"flushes"`: self.flushes
- `"buffer_depth"`: sum of len(v) for v in self._buffers.values()

### 3.3 Initialize batch writer in Ingestor

**File**: `services/ingest_iot/ingest.py`

In the `Ingestor.run` method (around line 461), AFTER the httpx client is created (line 464: `self.influx_client = httpx.AsyncClient(timeout=10.0)`), create and start the batch writer:

```python
self.batch_writer = InfluxBatchWriter(
    self.influx_client, INFLUXDB_URL, INFLUXDB_TOKEN,
    INFLUX_BATCH_SIZE, INFLUX_FLUSH_INTERVAL_MS
)
await self.batch_writer.start()
```

### 3.4 Replace direct writes with batch writer in db_worker

**File**: `services/ingest_iot/ingest.py`

In `db_worker`, find line 423 where `_write_influxdb` is called:
```python
await self._write_influxdb(tenant_id, device_id, site_id, msg_type, payload, event_ts)
```

Replace with the batch writer. Build the line protocol first, then add to batch:
```python
line = _build_line_protocol(msg_type, device_id, site_id, payload, event_ts)
if line:
    await self.batch_writer.add(tenant_id, line)
```

Keep the existing `_write_influxdb` method in the file (don't delete it) — it may be useful for one-off writes or debugging, but the main telemetry path now goes through the batch writer.

### 3.5 Add batch writer stats to periodic logging

**File**: `services/ingest_iot/ingest.py`

In the `stats_worker` method, add batch writer stats to the print. After the auth_cache stats (added in Task 001), add:

```python
batch_stats = self.batch_writer.stats()
```

And append to the print string:
```
f"influx_batch_ok={batch_stats['writes_ok']} influx_batch_err={batch_stats['writes_err']} influx_flushes={batch_stats['flushes']} influx_buffer={batch_stats['buffer_depth']}"
```

**Note**: `self.batch_writer` might not exist yet when stats_worker first runs (it's created in `run()` after tasks are started). Guard with `if hasattr(self, 'batch_writer'):` or initialize `self.batch_writer = None` in `__init__` and check for None.

### 3.6 Add env vars to docker-compose

**File**: `compose/docker-compose.yml`

In the `ingest` service environment section (after the AUTH_CACHE vars from Task 001):

```yaml
INFLUX_BATCH_SIZE: "${INFLUX_BATCH_SIZE:-500}"
INFLUX_FLUSH_INTERVAL_MS: "${INFLUX_FLUSH_INTERVAL_MS:-1000}"
```

---

## Files to Modify

| Action | Path | What changes |
|--------|------|--------------|
| MODIFY | `services/ingest_iot/ingest.py` | Add InfluxBatchWriter class, env vars, replace direct writes, stats logging |
| MODIFY | `compose/docker-compose.yml` | Add INFLUX_BATCH_* env vars to ingest service |

---

## Test

### Step 1: Run existing unit tests

```bash
cd /home/opsconductor/simcloud && python3 -m pytest tests/unit/ -v -x
```

### Step 2: Verify batch writer behavior

Read the code and confirm:
- [ ] Lines are buffered per tenant in `self._buffers`, not written immediately
- [ ] Flush triggers on batch_size OR flush_interval (whichever first)
- [ ] `_write_batch` sends all lines in a single HTTP POST with `\n` joined body
- [ ] Graceful shutdown (`stop()`) cancels flush task then flushes remaining buffers
- [ ] Stats track writes_ok, writes_err, flushes, buffer_depth
- [ ] `db_worker` builds line protocol and calls `batch_writer.add()` instead of `_write_influxdb()`

---

## Acceptance Criteria

- [ ] `InfluxBatchWriter` class with `add`, `flush_all`, `start`, `stop`, `stats`
- [ ] Per-tenant buffering with configurable batch_size and flush_interval
- [ ] Single HTTP POST per flush per tenant (not per message)
- [ ] Periodic flush background task
- [ ] Graceful shutdown flushes remaining data
- [ ] `db_worker` uses batch writer instead of direct `_write_influxdb`
- [ ] Batch stats logged periodically (with None guard)
- [ ] `INFLUX_BATCH_SIZE` and `INFLUX_FLUSH_INTERVAL_MS` env vars
- [ ] docker-compose.yml updated
- [ ] All existing unit tests pass

---

## Commit

```
Add batched InfluxDB writes for high-throughput ingestion

Replace per-message HTTP POSTs with a batch writer that buffers
line protocol per tenant and flushes on batch size (500) or
interval (1000ms). Reduces InfluxDB write overhead by ~100x at
high message rates.

Phase 14 Task 3: Batched InfluxDB Writes
```
