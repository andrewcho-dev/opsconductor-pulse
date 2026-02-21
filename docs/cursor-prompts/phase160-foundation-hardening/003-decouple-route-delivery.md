# Task 3: Decouple Route Delivery from Ingest Workers

## File to Modify

- `services/ingest_iot/ingest.py`

## Problem

Route delivery (webhooks, MQTT republish) runs **inline** inside `db_worker()` at lines 1532-1591. When `_deliver_to_route()` makes an HTTP call (10s timeout, line 1289), it blocks the entire db_worker coroutine. With 4 workers, 4 slow webhooks = all workers stalled = queue fills = data loss for all tenants.

The fix is straightforward: instead of delivering inline, push route matches to a separate async delivery queue processed by dedicated delivery workers.

## What to Do

### Step 1: Add a delivery queue and workers to Ingestor.__init__

Add alongside the existing `self.queue`:

```python
self._delivery_queue: asyncio.Queue = asyncio.Queue(maxsize=10000)
self._delivery_workers: list[asyncio.Task] = []
```

### Step 2: Create the delivery worker method

Add a new method to the Ingestor class:

```python
async def _route_delivery_worker(self):
    """Process route delivery jobs from the delivery queue."""
    while True:
        try:
            job = await self._delivery_queue.get()
        except asyncio.CancelledError:
            break

        route = job["route"]
        topic = job["topic"]
        payload = job["payload"]
        tenant_id = job["tenant_id"]

        try:
            await self._deliver_to_route(route, topic, payload, tenant_id)
            logger.debug(
                "route_delivered",
                extra={"route_id": route["id"], "destination": route["destination_type"]},
            )
        except Exception as route_exc:
            # Write to dead letter queue (same logic as current inline handler)
            try:
                assert self.pool is not None
                async with self.pool.acquire() as conn:
                    await _set_tenant_write_context(conn, tenant_id)
                    await conn.execute(
                        """
                        INSERT INTO dead_letter_messages
                            (tenant_id, route_id, original_topic, payload,
                             destination_type, destination_config, error_message)
                        VALUES ($1, $2, $3, $4::jsonb, $5, $6::jsonb, $7)
                        """,
                        tenant_id,
                        route["id"],
                        topic,
                        json.dumps(payload, default=str),
                        route["destination_type"],
                        json.dumps(route.get("destination_config") or {}, default=str),
                        str(route_exc)[:2000],
                    )
            except Exception as dlq_exc:
                logger.error(
                    "dlq_write_failed",
                    extra={"route_id": route["id"], "error": str(dlq_exc)},
                )
            logger.warning(
                "route_delivery_failed_dlq",
                extra={
                    "route_id": route["id"],
                    "error": str(route_exc),
                    "destination": route["destination_type"],
                },
            )
        finally:
            self._delivery_queue.task_done()
```

### Step 3: Start delivery workers in run()

In the `run()` method, after creating db_workers (around line 1839), add:

```python
# Start route delivery workers (separate from telemetry ingest workers)
DELIVERY_WORKER_COUNT = int(os.getenv("DELIVERY_WORKER_COUNT", "2"))
for i in range(DELIVERY_WORKER_COUNT):
    task = asyncio.create_task(self._route_delivery_worker())
    self._delivery_workers.append(task)
```

### Step 4: Replace inline delivery in db_worker

Replace the entire route delivery block in `db_worker()` (lines 1532-1591). Change from:

```python
# --- Message route fan-out ---
try:
    routes = await self._get_message_routes(tenant_id)
    for route in routes:
        try:
            if not mqtt_topic_matches(route["topic_filter"], topic):
                continue
            if route.get("payload_filter"):
                pf = route["payload_filter"]
                if isinstance(pf, str):
                    pf = json.loads(pf)
                if not evaluate_payload_filter(pf, payload):
                    continue
            if route["destination_type"] == "postgresql":
                continue  # Already written

            await self._deliver_to_route(route, topic, payload, tenant_id)
            # ... logging ...
        except Exception as route_exc:
            # ... DLQ write ...
except Exception as route_fan_exc:
    logger.warning("route_fanout_error", extra={"error": str(route_fan_exc)})
```

To:

```python
# --- Message route fan-out (enqueue for async delivery) ---
try:
    routes = await self._get_message_routes(tenant_id)
    for route in routes:
        try:
            if not mqtt_topic_matches(route["topic_filter"], topic):
                continue
            if route.get("payload_filter"):
                pf = route["payload_filter"]
                if isinstance(pf, str):
                    pf = json.loads(pf)
                if not evaluate_payload_filter(pf, payload):
                    continue
            if route["destination_type"] == "postgresql":
                continue  # Already written

            # Enqueue for async delivery instead of delivering inline
            try:
                self._delivery_queue.put_nowait({
                    "route": route,
                    "topic": topic,
                    "payload": payload,
                    "tenant_id": tenant_id,
                })
            except asyncio.QueueFull:
                logger.warning(
                    "delivery_queue_full",
                    extra={"route_id": route["id"], "tenant_id": tenant_id},
                )
        except Exception as route_match_exc:
            logger.warning(
                "route_match_error",
                extra={"route_id": route.get("id"), "error": str(route_match_exc)},
            )
except Exception as route_fan_exc:
    logger.warning("route_fanout_error", extra={"error": str(route_fan_exc)})
```

### Step 5: Add delivery workers to graceful shutdown

In the `shutdown()` method (from Task 1), after draining the main queue and stopping db_workers, add:

```python
    # 3b. Wait for delivery queue to drain
    if self._delivery_queue:
        drain_start = time.time()
        while not self._delivery_queue.empty() and (time.time() - drain_start) < 5:
            await asyncio.sleep(0.1)

    # 3c. Cancel delivery workers
    for task in self._delivery_workers:
        task.cancel()
    if self._delivery_workers:
        await asyncio.gather(*self._delivery_workers, return_exceptions=True)
        logger.info("delivery_workers_stopped")
```

### Step 6: Add delivery queue stats to health/metrics

In the `stats_worker()` logging and the `/health` endpoint, add `delivery_queue_depth`:

```python
"delivery_queue_depth": self._delivery_queue.qsize(),
```

And add a Prometheus gauge:

```python
delivery_queue_depth = Gauge("pulse_ingest_delivery_queue_depth", "Route delivery queue depth")
```

Update it in the stats loop.

### Step 7: Add env var to docker-compose.yml

Add to the ingest service environment in `compose/docker-compose.yml`:

```yaml
      # DELIVERY_WORKER_COUNT: "2"   # Async route delivery workers (default: 2)
```

## Important Notes

- This change is **transparent to route behavior** — routes are still matched, delivered, and DLQ'd the same way. The only difference is delivery happens asynchronously.
- The delivery queue has a 10K limit. If it fills (extremely high route volume), new deliveries are dropped with a warning log. This is a safeguard — in practice, route delivery should be fast relative to telemetry volume.
- With 2 delivery workers and 10s webhook timeout, worst case is 2 concurrent slow webhooks without blocking any telemetry processing.
- The `_deliver_to_route()` method itself doesn't change — only where it's called from.
- MQTT republish within `_deliver_to_route()` uses `self._mqtt_client.publish()` which is non-blocking, so those won't stall. But it still benefits from being off the db_worker path.

## Verification

```bash
# Check that db_worker no longer calls _deliver_to_route directly
grep -n '_deliver_to_route' services/ingest_iot/ingest.py
# Should only appear in: method definition + _route_delivery_worker (not in db_worker)

# Check delivery queue is created
grep -n 'delivery_queue\|delivery_worker' services/ingest_iot/ingest.py
```
