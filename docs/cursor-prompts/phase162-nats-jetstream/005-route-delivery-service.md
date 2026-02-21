# Task 5: Route Delivery Service via NATS

## Files to Create/Modify

- **Create:** `services/route_delivery/delivery.py` — new dedicated service
- **Create:** `services/route_delivery/Dockerfile`
- **Create:** `services/route_delivery/requirements.txt`
- **Modify:** `compose/docker-compose.yml` — add route-delivery service

## What to Do

Create a dedicated service that consumes route delivery jobs from the NATS `ROUTES` stream and delivers them to webhook/MQTT destinations with retry support.

This replaces:
- The inline `_deliver_to_route()` in the ingest db_worker (Phase 160 decoupled it to a local queue)
- The `_delivery_queue` from Phase 160 (now NATS is the queue)

### Step 1: Create the delivery service

Create `services/route_delivery/delivery.py`:

```python
"""
Route Delivery Service
Consumes route delivery jobs from NATS ROUTES stream.
Delivers to webhook and MQTT republish destinations with retry.
"""
import os
import json
import logging
import asyncio
import signal
import time
import hashlib
import hmac as hmac_mod
from datetime import datetime, timezone

import httpx
import nats
import asyncpg

logger = logging.getLogger("route_delivery")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")

NATS_URL = os.getenv("NATS_URL", "nats://localhost:4222")
DATABASE_URL = os.getenv("DATABASE_URL")
PG_HOST = os.getenv("PG_HOST", "localhost")
PG_PORT = int(os.getenv("PG_PORT", "5432"))
PG_DB = os.getenv("PG_DB", "iotcloud")
PG_USER = os.getenv("PG_USER", "iot")
PG_PASS = os.getenv("PG_PASS", "")
WORKER_COUNT = int(os.getenv("DELIVERY_WORKER_COUNT", "4"))
WEBHOOK_TIMEOUT = float(os.getenv("WEBHOOK_TIMEOUT_SECONDS", "10"))

# Optional: MQTT client for republish destinations
MQTT_HOST = os.getenv("MQTT_HOST")
MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))
MQTT_USERNAME = os.getenv("MQTT_USERNAME")
MQTT_PASSWORD = os.getenv("MQTT_PASSWORD")


class RouteDeliveryService:
    def __init__(self):
        self._nc = None
        self._js = None
        self._sub = None
        self._pool = None
        self._mqtt_client = None
        self._shutting_down = False
        self._workers = []
        # Counters
        self.delivered = 0
        self.failed = 0

    async def init_db(self):
        """Initialize DB pool for DLQ writes."""
        if DATABASE_URL:
            self._pool = await asyncpg.create_pool(dsn=DATABASE_URL, min_size=1, max_size=5, command_timeout=30)
        else:
            self._pool = await asyncpg.create_pool(
                host=PG_HOST, port=PG_PORT, database=PG_DB,
                user=PG_USER, password=PG_PASS,
                min_size=1, max_size=5, command_timeout=30,
            )

    async def init_nats(self):
        """Connect to NATS."""
        self._nc = await nats.connect(NATS_URL)
        self._js = self._nc.jetstream()
        self._sub = await self._js.pull_subscribe(
            subject="routes.>",
            durable="route-delivery",
            stream="ROUTES",
        )
        logger.info("nats_connected")

    async def init_mqtt(self):
        """Initialize MQTT client for republish destinations."""
        if not MQTT_HOST:
            return
        try:
            import paho.mqtt.client as paho_mqtt
            self._mqtt_client = paho_mqtt.Client()
            if MQTT_USERNAME and MQTT_PASSWORD:
                self._mqtt_client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)
            self._mqtt_client.connect(MQTT_HOST, MQTT_PORT, keepalive=60)
            self._mqtt_client.loop_start()
            logger.info("mqtt_connected_for_republish")
        except Exception as e:
            logger.warning("mqtt_connect_failed", extra={"error": str(e)})

    async def deliver(self, job: dict):
        """Deliver a single route job."""
        route = job["route"]
        topic = job["topic"]
        payload = job["payload"]
        tenant_id = job["tenant_id"]
        dest_type = route["destination_type"]
        config = route.get("destination_config") or {}

        if dest_type == "webhook":
            url = config.get("url")
            if not url:
                return
            method = config.get("method", "POST").upper()
            headers = {"Content-Type": "application/json"}

            body_bytes = json.dumps(payload, default=str).encode()
            secret = config.get("secret")
            if secret:
                sig_hex = hmac_mod.new(secret.encode(), body_bytes, hashlib.sha256).hexdigest()
                headers["X-Signature-256"] = f"sha256={sig_hex}"

            async with httpx.AsyncClient(timeout=WEBHOOK_TIMEOUT) as client:
                resp = await client.request(method, url, content=body_bytes, headers=headers)
                if resp.status_code >= 400:
                    raise Exception(f"Webhook returned HTTP {resp.status_code}")

        elif dest_type == "mqtt_republish":
            republish_topic = config.get("topic")
            if not republish_topic:
                return
            republish_topic = republish_topic.replace("{tenant_id}", tenant_id)
            republish_topic = republish_topic.replace("{device_id}", payload.get("device_id", ""))

            if self._mqtt_client:
                msg_bytes = json.dumps(payload, default=str).encode()
                self._mqtt_client.publish(republish_topic, msg_bytes)
            else:
                raise Exception("MQTT client not available for republish")

        elif dest_type == "postgresql":
            return  # Already written by ingest worker

    async def write_dlq(self, job: dict, error: str):
        """Write failed delivery to dead letter queue."""
        if not self._pool:
            return
        route = job["route"]
        try:
            async with self._pool.acquire() as conn:
                # Set tenant context for RLS
                await conn.execute("SET LOCAL ROLE pulse_app")
                await conn.execute(
                    "SELECT set_config('app.tenant_id', $1, true)",
                    job["tenant_id"],
                )
                await conn.execute(
                    """
                    INSERT INTO dead_letter_messages
                        (tenant_id, route_id, original_topic, payload,
                         destination_type, destination_config, error_message)
                    VALUES ($1, $2, $3, $4::jsonb, $5, $6::jsonb, $7)
                    """,
                    job["tenant_id"],
                    route["id"],
                    job["topic"],
                    json.dumps(job["payload"], default=str),
                    route["destination_type"],
                    json.dumps(route.get("destination_config") or {}, default=str),
                    error[:2000],
                )
        except Exception as dlq_err:
            logger.error("dlq_write_failed", extra={"error": str(dlq_err)})

    async def worker(self, worker_id: int):
        """Pull and deliver route jobs from NATS."""
        logger.info("delivery_worker_started", extra={"worker_id": worker_id})

        while not self._shutting_down:
            try:
                msgs = await self._sub.fetch(batch=10, timeout=1.0)
            except Exception as e:
                if "timeout" in str(e).lower():
                    continue
                logger.warning("nats_fetch_error", extra={"error": str(e)})
                await asyncio.sleep(0.5)
                continue

            for msg in msgs:
                try:
                    job = json.loads(msg.data.decode())
                    await self.deliver(job)
                    await msg.ack()
                    self.delivered += 1
                except Exception as e:
                    logger.warning("delivery_failed", extra={
                        "error": str(e),
                        "route_id": job.get("route", {}).get("id"),
                    })
                    self.failed += 1

                    # Check if we've exceeded max retries
                    # NATS tracks delivery count; if max_deliver is reached,
                    # the message is dropped. We write to DLQ on final attempt.
                    metadata = msg.metadata
                    if metadata and metadata.num_delivered >= 3:
                        await self.write_dlq(job, str(e))
                        await msg.term()  # Terminal failure — stop redelivery
                    else:
                        await msg.nak()  # NAK for redelivery

    async def shutdown(self):
        """Graceful shutdown."""
        logger.info("shutdown_initiated")
        self._shutting_down = True

        for task in self._workers:
            task.cancel()
        if self._workers:
            await asyncio.gather(*self._workers, return_exceptions=True)

        if self._nc:
            await self._nc.drain()
        if self._pool:
            await self._pool.close()
        if self._mqtt_client:
            self._mqtt_client.loop_stop()
            self._mqtt_client.disconnect()

        logger.info("shutdown_complete", extra={
            "delivered": self.delivered, "failed": self.failed,
        })

    async def run(self):
        await self.init_db()
        await self.init_nats()
        await self.init_mqtt()

        self._workers = []
        for i in range(WORKER_COUNT):
            self._workers.append(asyncio.create_task(self.worker(i)))

        # Wait for shutdown signal
        shutdown_event = asyncio.Event()
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(sig, shutdown_event.set)
        await shutdown_event.wait()
        await self.shutdown()


async def main():
    svc = RouteDeliveryService()
    await svc.run()

if __name__ == "__main__":
    asyncio.run(main())
```

### Step 2: Create Dockerfile

Create `services/route_delivery/Dockerfile`:

```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY route_delivery/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY route_delivery/ .
CMD ["python", "delivery.py"]
```

### Step 3: Create requirements.txt

Create `services/route_delivery/requirements.txt`:

```
nats-py>=2.7.0
asyncpg>=0.29.0
httpx>=0.27.0
paho-mqtt>=1.6.1,<2.0
```

### Step 4: Add to docker-compose.yml

```yaml
  route-delivery:
    build:
      context: ../services
      dockerfile: route_delivery/Dockerfile
    container_name: iot-route-delivery
    environment:
      NATS_URL: "nats://iot-nats:4222"
      DATABASE_URL: "postgresql://iot:${PG_PASS}@iot-pgbouncer:5432/iotcloud"
      MQTT_HOST: iot-mqtt
      MQTT_PORT: "1883"
      MQTT_USERNAME: "service_pulse"
      MQTT_PASSWORD: ${MQTT_ADMIN_PASSWORD}
      DELIVERY_WORKER_COUNT: "4"
      WEBHOOK_TIMEOUT_SECONDS: "10"
    depends_on:
      nats:
        condition: service_healthy
      pgbouncer:
        condition: service_healthy
    restart: unless-stopped
```

### Step 5: Remove delivery queue from ingest service

After this service is running, remove from `services/ingest_iot/ingest.py`:
- `self._delivery_queue`
- `self._delivery_workers`
- `_route_delivery_worker()` method
- `DELIVERY_WORKER_COUNT` env var (now in route-delivery service)
- Any references to the local delivery queue

The ingest service now just publishes route matches to NATS `routes.{tenant_id}`.

## Important Notes

- **Retry semantics:** NATS `max_deliver=3` means each message gets 3 attempts. On the 3rd failure, it's written to DLQ and terminated. This is automatic retry without custom retry logic.
- **Backoff:** NATS has configurable `ack_wait` (30s). If a consumer doesn't ACK within 30s, the message is redelivered. Combined with `max_deliver=3`, this provides exponential-like backoff behavior.
- **This service is stateless** — it can be horizontally scaled by adding more pods. They all join the same `route-delivery` consumer group.
- **MQTT republish** requires the route-delivery service to connect to the MQTT broker. This is the same `service_pulse` credentials on port 1883.
- **Monitoring:** Add a `/health` endpoint (similar to ingest) that reports delivered/failed counts and NATS connection status.

## Verification

```bash
# Publish a test route job to NATS
docker exec iot-nats-init nats pub routes.test-tenant \
  '{"route":{"id":1,"destination_type":"webhook","destination_config":{"url":"http://iot-webhook-receiver:9999/test"}},"topic":"test","payload":{"test":1},"tenant_id":"test-tenant"}' \
  --server nats://iot-nats:4222

# Check delivery logs
docker compose logs --tail 10 route-delivery

# Check consumer info
docker exec iot-nats-init nats consumer info ROUTES route-delivery --server nats://iot-nats:4222
```
