# Task 1: Graceful Shutdown for Ingest Service

## Files to Modify

- `services/ingest_iot/ingest.py`

## Problem

The ingest service has no signal handlers. When Docker sends SIGTERM (on deploy/restart), the process terminates immediately, losing:
- Records buffered in the batch writer (up to 500 records or 1s of data)
- Messages in the asyncio.Queue (up to 50K messages)
- In-flight db_worker processing

The `TimescaleBatchWriter` already has a `stop()` method (in `shared/ingest_core.py:157-167`) that cancels the flush loop and calls `_flush()` one final time — but it is **never called**.

## What to Do

### Step 1: Add a shutdown flag to Ingestor

Add an instance variable in `__init__`:

```python
self._shutting_down = False
```

### Step 2: Add a graceful shutdown method

Add this method to the `Ingestor` class:

```python
async def shutdown(self):
    """Graceful shutdown: stop accepting messages, drain queue, flush writes."""
    logger.info("shutdown_initiated")
    self._shutting_down = True

    # 1. Stop MQTT client (stops receiving new messages)
    if self._mqtt_client:
        self._mqtt_client.loop_stop()
        self._mqtt_client.disconnect()
        logger.info("mqtt_disconnected")

    # 2. Wait for queue to drain (with timeout)
    if self.queue:
        drain_timeout = 10  # seconds
        start = time.time()
        while not self.queue.empty() and (time.time() - start) < drain_timeout:
            await asyncio.sleep(0.1)
        remaining = self.queue.qsize()
        if remaining:
            logger.warning("queue_drain_timeout", extra={"remaining": remaining})
        else:
            logger.info("queue_drained")

    # 3. Cancel worker tasks and wait for in-flight work to finish
    for task in self._workers:
        task.cancel()
    if self._workers:
        await asyncio.gather(*self._workers, return_exceptions=True)
        logger.info("workers_stopped")

    # 4. Flush the batch writer (this is the critical step)
    if self.batch_writer:
        await self.batch_writer.stop()
        logger.info("batch_writer_flushed", extra={
            "records_written": self.batch_writer.records_written,
            "batches_flushed": self.batch_writer.batches_flushed,
        })

    # 5. Close DB pool
    if self.pool:
        await self.pool.close()
        logger.info("db_pool_closed")

    logger.info("shutdown_complete")
```

### Step 3: Replace the infinite loop with signal-aware wait

Replace the current `run()` ending (lines 1864-1865):

```python
        while True:
            await asyncio.sleep(5)
```

With:

```python
        # Wait for shutdown signal
        shutdown_event = asyncio.Event()

        def _signal_handler():
            logger.info("signal_received")
            shutdown_event.set()

        loop = asyncio.get_running_loop()
        for sig in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(sig, _signal_handler)

        await shutdown_event.wait()
        await self.shutdown()
```

### Step 4: Add signal import

Add `signal` to the imports at the top of the file if not already present:

```python
import signal
```

### Step 5: Guard the on_message enqueue

In `on_message`, check the shutdown flag before enqueuing. Find the `_enqueue` inner function and add a guard:

```python
def _enqueue():
    if self._shutting_down:
        return
    # ... existing enqueue logic
```

This prevents new messages from entering the queue during shutdown.

## Important Notes

- The `TimescaleBatchWriter.stop()` method already exists and works correctly — it cancels the flush task, then calls `_flush()` one final time to write remaining records. We just need to call it.
- Docker's default SIGTERM timeout is 10 seconds. If the shutdown takes longer, Docker sends SIGKILL. The drain timeout (10s) plus flush time should fit within this window. If needed, increase Docker's `stop_grace_period` in docker-compose.yml to 30s:
  ```yaml
  ingest:
    stop_grace_period: 30s
  ```
- The `signal` module's `add_signal_handler` only works on Unix and must be called from the main thread — this is the case here since `run()` is called from `asyncio.run(main())`.
- Worker task cancellation will raise `CancelledError` in the `db_worker` coroutine. The `asyncio.gather(..., return_exceptions=True)` handles this gracefully.

## Verification

```bash
# Start the ingest service, then send SIGTERM and check logs for shutdown sequence
docker compose up -d ingest
sleep 3
docker compose logs --tail 5 ingest  # should show "mqtt connected"
docker compose kill -s SIGTERM ingest
docker compose logs --tail 20 ingest  # should show shutdown_initiated → mqtt_disconnected → queue_drained → workers_stopped → batch_writer_flushed → shutdown_complete
```
