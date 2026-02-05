# Task 004: Multi-Worker Ingest Pipeline

> **CURSOR: EXECUTE THIS TASK**
>
> Read the instructions below and implement them exactly.
> Modify only the files listed in "Files to Modify".
> RUN THE TESTS in the Test section. Do not proceed if tests fail.
> IMPORTANT: Do not commit until all tests pass.

---

## Context

**THE PROBLEM**: The ingest pipeline has a single `db_worker` async task consuming from the asyncio.Queue (started at line 467). Even with the auth cache (Task 001) and batch writer (Task 003), a single worker limits throughput because it processes messages sequentially: validate -> rate limit -> build line protocol -> enqueue to batch writer. With multiple workers pulling from the same queue, we get concurrent message processing.

**Read first**:
- `services/ingest_iot/ingest.py` — focus on:
  - `Ingestor.__init__` (line 162) where `self.queue` is created with `maxsize=20000`
  - `Ingestor.run` (line 461) where `asyncio.create_task(self.db_worker())` starts a single worker (line 467)
  - `asyncpg.create_pool` call (lines 189-191) with `min_size=1, max_size=5`

---

## Task

### 4.1 Add environment variables

**File**: `services/ingest_iot/ingest.py`

Add near the other env vars (after `INFLUX_FLUSH_INTERVAL_MS` from Task 003):

```python
INGEST_WORKER_COUNT = int(os.getenv("INGEST_WORKER_COUNT", "4"))
INGEST_QUEUE_SIZE = int(os.getenv("INGEST_QUEUE_SIZE", "50000"))
```

### 4.2 Increase queue size

**File**: `services/ingest_iot/ingest.py`

Find where `asyncio.Queue(maxsize=20000)` is created in `Ingestor.__init__` (line 165). Change it to:
```python
self.queue: asyncio.Queue = asyncio.Queue(maxsize=INGEST_QUEUE_SIZE)
```

### 4.3 Increase asyncpg pool size

**File**: `services/ingest_iot/ingest.py`

Find the `asyncpg.create_pool` call in `init_db` (lines 189-191). Change the pool parameters from:
```python
min_size=1, max_size=5
```
to:
```python
min_size=2, max_size=10
```

### 4.4 Start multiple workers

**File**: `services/ingest_iot/ingest.py`

In the `run` method (around line 467), find where the single `db_worker` task is created:
```python
asyncio.create_task(self.db_worker())
```

Replace with a loop that starts N workers:
```python
self._workers = []
for i in range(INGEST_WORKER_COUNT):
    task = asyncio.create_task(self.db_worker())
    self._workers.append(task)
```

Each worker pulls from the same shared `self.queue`. asyncio.Queue is safe for multiple async consumers.

### 4.5 Add worker count to stats logging

**File**: `services/ingest_iot/ingest.py`

In the `stats_worker` method's print statement, add pipeline info. Append:

```
f"workers={INGEST_WORKER_COUNT} queue_max={INGEST_QUEUE_SIZE} queue_depth={self.queue.qsize()}"
```

### 4.6 Add env vars to docker-compose

**File**: `compose/docker-compose.yml`

In the `ingest` service environment section (after the INFLUX_BATCH vars from Task 003):

```yaml
INGEST_WORKER_COUNT: "${INGEST_WORKER_COUNT:-4}"
INGEST_QUEUE_SIZE: "${INGEST_QUEUE_SIZE:-50000}"
```

---

## Files to Modify

| Action | Path | What changes |
|--------|------|--------------|
| MODIFY | `services/ingest_iot/ingest.py` | Env vars, queue size, pool size, multi-worker startup, stats |
| MODIFY | `compose/docker-compose.yml` | Add INGEST_WORKER_COUNT, INGEST_QUEUE_SIZE env vars |

---

## Test

### Step 1: Run existing unit tests

```bash
cd /home/opsconductor/simcloud && python3 -m pytest tests/unit/ -v -x
```

### Step 2: Verify multi-worker setup

Read the code and confirm:
- [ ] `INGEST_WORKER_COUNT` workers are started in a loop (not just 1)
- [ ] All workers share the same `self.queue`
- [ ] All workers share the same `self.auth_cache` and `self.batch_writer`
- [ ] Queue maxsize uses `INGEST_QUEUE_SIZE` env var (default 50000)
- [ ] asyncpg pool has `min_size=2, max_size=10`
- [ ] Worker count and queue depth are logged in stats

---

## Acceptance Criteria

- [ ] N worker tasks started (configurable via `INGEST_WORKER_COUNT`, default 4)
- [ ] Queue maxsize configurable via `INGEST_QUEUE_SIZE` (default 50000)
- [ ] asyncpg pool sized at (2, 10)
- [ ] All workers share the same queue, cache, and batch writer
- [ ] Stats log includes worker count and queue depth
- [ ] docker-compose.yml updated with new env vars
- [ ] All existing unit tests pass

---

## Commit

```
Scale ingest pipeline to multiple concurrent workers

Start N async workers (default 4) consuming from the shared queue.
Increase queue capacity from 20k to 50k and asyncpg pool from
(1,5) to (2,10). Combined with auth cache and batch writer, this
enables ~2000 msg/sec per ingest instance.

Phase 14 Task 4: Multi-Worker Ingest Pipeline
```
