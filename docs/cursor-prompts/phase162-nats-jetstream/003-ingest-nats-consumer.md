# Task 3: Refactor Ingest Service — MQTT Subscriber → NATS Consumer

## File to Modify

- `services/ingest_iot/ingest.py` (major refactor)
- `services/ingest_iot/requirements.txt` (add `nats-py`)

## What to Do

This is the largest code change in the rearchitecture. The ingest service currently:
1. Connects to MQTT broker as a subscriber
2. Receives messages via `on_message` callback
3. Enqueues to `asyncio.Queue(50000)`
4. 4 `db_worker` tasks pull from queue and process

After this change:
1. Connects to NATS JetStream as a pull consumer
2. Pulls messages in batches from the `ingest-workers` consumer group
3. Processes through the same validation/batch-write pipeline
4. ACKs messages after successful processing

The `asyncio.Queue` is **removed** — NATS IS the queue.

### Step 1: Add nats-py dependency

Add to `services/ingest_iot/requirements.txt`:

```
nats-py>=2.7.0
```

### Step 2: Add NATS connection to Ingestor

Add new instance variables in `__init__`:

```python
self._nc = None        # NATS connection
self._js = None        # JetStream context
self._nats_sub = None  # Pull subscription
```

Add a NATS connection method:

```python
async def init_nats(self):
    """Connect to NATS JetStream."""
    import nats
    nats_url = os.getenv("NATS_URL", "nats://localhost:4222")
    self._nc = await nats.connect(nats_url)
    self._js = self._nc.jetstream()
    logger.info("nats_connected", extra={"url": nats_url})
```

### Step 3: Replace the run() method's MQTT section with NATS consumption

Replace the MQTT connection and infinite loop in `run()` (lines 1842-1865) with:

```python
    # Connect to NATS
    await self.init_nats()

    # Subscribe to TELEMETRY stream as pull consumer
    self._nats_sub = await self._js.pull_subscribe(
        subject="telemetry.>",
        durable="ingest-workers",
        stream="TELEMETRY",
    )

    # Also subscribe to SHADOW and COMMANDS
    self._shadow_sub = await self._js.pull_subscribe(
        subject="shadow.>",
        durable="ingest-shadow",
        stream="SHADOW",
    )
    self._commands_sub = await self._js.pull_subscribe(
        subject="commands.>",
        durable="ingest-commands",
        stream="COMMANDS",
    )

    # Start NATS consumer workers (replace db_workers)
    self._workers = []
    for i in range(INGEST_WORKER_COUNT):
        task = asyncio.create_task(self._nats_telemetry_worker(i))
        self._workers.append(task)

    # Shadow and command workers (fewer needed)
    asyncio.create_task(self._nats_shadow_worker())
    asyncio.create_task(self._nats_commands_worker())

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

### Step 4: Create the NATS telemetry worker

This replaces `db_worker()`. The core validation and batch-write logic stays the same — only the message source changes:

```python
async def _nats_telemetry_worker(self, worker_id: int):
    """Pull messages from NATS TELEMETRY stream and process them."""
    logger.info("nats_worker_started", extra={"worker_id": worker_id})

    while not self._shutting_down:
        try:
            # Pull batch of messages (up to 50, wait up to 1s)
            msgs = await self._nats_sub.fetch(batch=50, timeout=1.0)
        except Exception as fetch_err:
            if "timeout" in str(fetch_err).lower():
                continue  # No messages available, loop back
            logger.warning("nats_fetch_error", extra={"error": str(fetch_err)})
            await asyncio.sleep(0.5)
            continue

        for msg in msgs:
            try:
                # Parse the NATS message envelope
                envelope = json.loads(msg.data.decode())
                topic = envelope.get("topic", "")
                payload = envelope.get("payload", {})
                mqtt_username = envelope.get("username", "")

                if isinstance(payload, str):
                    payload = json.loads(payload)

                # Extract tenant/device from topic (same as existing topic_extract)
                tenant_id, device_id, msg_type = topic_extract(topic)
                if tenant_id is None or device_id is None:
                    await self._insert_quarantine(
                        topic, None, None, None, None,
                        "BAD_TOPIC_FORMAT", payload, None,
                    )
                    await msg.ack()
                    continue

                # ─── EXISTING VALIDATION PIPELINE ───
                # (Reuse the exact same logic from the current db_worker)
                # - site_id extraction and validation
                # - Tenant mismatch check
                # - Device registry lookup
                # - Device status check (revoked, etc.)
                # - Subscription check
                # - Certificate auth validation
                # - Provision token validation
                # - Rate limiting
                # - Payload size/metric validation
                # - Sensor auto-discovery
                # - Batch writer add
                # - Route matching → publish to routes.{tenant_id} on NATS
                #
                # Extract this logic from the existing db_worker into a
                # reusable method like:
                #   await self._process_telemetry(topic, payload, tenant_id,
                #                                 device_id, msg_type, mqtt_username)

                await self._process_telemetry(
                    topic, payload, tenant_id, device_id, msg_type, mqtt_username
                )

                # ACK the message (tells NATS we're done with it)
                await msg.ack()

            except Exception as proc_err:
                logger.error("nats_process_error", extra={
                    "error": str(proc_err), "worker_id": worker_id,
                })
                # NAK the message (NATS will redeliver, up to max_deliver times)
                await msg.nak()
```

### Step 5: Extract _process_telemetry from db_worker

The existing `db_worker()` method (lines ~1350-1593) contains the full validation pipeline. Extract the inner logic (everything after the `queue.get()` and JSON parse) into a standalone method:

```python
async def _process_telemetry(self, topic: str, payload: dict, tenant_id: str,
                              device_id: str, msg_type: str, mqtt_username: str = ""):
    """
    Process a single telemetry message through the validation pipeline.
    Extracted from the original db_worker() for reuse by NATS and HTTP paths.
    """
    # ... (the entire validation + batch_writer.add + route matching logic)
    # This is the bulk of the current db_worker content from line ~1370 to ~1593
    # with the route delivery changed to publish to NATS instead of inline delivery
```

For route matching, instead of calling `_deliver_to_route()` or enqueuing to `_delivery_queue`, publish to NATS:

```python
# Instead of inline delivery or local delivery queue:
try:
    await self._nc.publish(
        f"routes.{tenant_id}",
        json.dumps({
            "route": route,
            "topic": topic,
            "payload": payload,
            "tenant_id": tenant_id,
        }, default=str).encode(),
    )
except Exception as pub_err:
    logger.warning("route_publish_error", extra={"error": str(pub_err)})
```

### Step 6: Create shadow and command workers

These are simpler — they handle shadow reported and command ack messages:

```python
async def _nats_shadow_worker(self):
    """Process shadow/reported updates from NATS."""
    while not self._shutting_down:
        try:
            msgs = await self._shadow_sub.fetch(batch=20, timeout=1.0)
        except Exception:
            await asyncio.sleep(0.5)
            continue
        for msg in msgs:
            try:
                envelope = json.loads(msg.data.decode())
                # Reuse existing shadow handling logic
                # (currently in on_message for SHADOW_REPORTED_TOPIC)
                await self._handle_shadow_reported(envelope)
                await msg.ack()
            except Exception as e:
                logger.error("shadow_process_error", extra={"error": str(e)})
                await msg.nak()
```

### Step 7: Update shutdown to close NATS

In the `shutdown()` method, add after stopping workers:

```python
    # Close NATS connection
    if self._nc:
        await self._nc.drain()
        logger.info("nats_connection_closed")
```

### Step 8: Remove MQTT client code

Once NATS consumption is working:
- Remove `on_connect`, `on_message` callbacks
- Remove `paho-mqtt` from requirements (but keep it if `_deliver_to_route` still uses it for MQTT republish — or use the NATS-based route delivery from Task 5)
- Remove the `asyncio.Queue` and its size configuration
- Remove `MQTT_HOST`, `MQTT_PORT`, `MQTT_USERNAME`, `MQTT_PASSWORD` env vars from ingest service (these were for the direct broker subscription — the ingest service no longer connects to MQTT)

**Keep the `_mqtt_client` reference if the ops_worker or other services still need to publish to MQTT** (e.g., for device shadow desired state, command responses). This may need to be a separate MQTT publisher client, not tied to the subscription lifecycle.

### Step 9: Update docker-compose ingest environment

```yaml
  ingest:
    environment:
      NATS_URL: "nats://iot-nats:4222"
      # Remove MQTT_HOST, MQTT_PORT, MQTT_USERNAME, MQTT_PASSWORD
      # (ingest no longer subscribes to MQTT directly)
      # Keep PG_*, BATCH_SIZE, FLUSH_INTERVAL_MS, INGEST_WORKER_COUNT, etc.
    depends_on:
      nats:
        condition: service_healthy
      postgres:
        condition: service_healthy
```

## Important Notes

- **The validation pipeline doesn't change** — same device registry lookup, same auth check, same rate limiting, same batch writer. Only the message source changes (NATS instead of MQTT).
- **ACK semantics:** Messages are only ACK'd after successful processing. If the worker crashes mid-processing, NATS will redeliver the message (up to `max_deliver` times).
- **Consumer groups:** Multiple ingest pods joining the `ingest-workers` consumer will automatically load-balance messages. No config changes needed.
- **fetch batch size:** Start with `batch=50`. Tune based on processing latency. Larger batches = higher throughput but more latency variance.
- **Gradual migration:** You can run both the old MQTT subscriber AND the new NATS consumer simultaneously during the transition. Just ensure messages aren't processed twice (use a feature flag or env var to toggle which path is active).
- **nats-py async:** The `nats-py` library is fully async and compatible with the existing asyncio architecture.

## Verification

```bash
# Publish test message to NATS directly
docker exec iot-nats-init nats pub telemetry.test-tenant \
  '{"topic":"tenant/test-tenant/device/dev1/telemetry","tenant_id":"test-tenant","device_id":"dev1","msg_type":"telemetry","payload":{"site_id":"s1","provision_token":"tok","metrics":{"temp":22}}}' \
  --server nats://iot-nats:4222

# Check ingest worker processed it
docker compose logs --tail 10 ingest | grep "messages_written\|nats_worker"

# Check consumer lag
docker exec iot-nats-init nats consumer info TELEMETRY ingest-workers --server nats://iot-nats:4222
```
