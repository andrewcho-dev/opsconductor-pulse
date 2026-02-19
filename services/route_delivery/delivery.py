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
import hashlib
import hmac as hmac_mod

import httpx
import nats
import asyncpg

logger = logging.getLogger("route_delivery")
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s"
)

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
MQTT_TLS = os.getenv("MQTT_TLS", "true").lower() == "true"
MQTT_TLS_INSECURE = os.getenv("MQTT_TLS_INSECURE", "true").lower() == "true"


class RouteDeliveryService:
    def __init__(self):
        self._nc = None
        self._js = None
        self._sub = None
        self._pool = None
        self._mqtt_client = None
        self._shutting_down = False
        self._workers = []
        self.delivered = 0
        self.failed = 0

    async def init_db(self):
        """Initialize DB pool for DLQ writes."""
        if DATABASE_URL:
            self._pool = await asyncpg.create_pool(
                dsn=DATABASE_URL, min_size=1, max_size=5, command_timeout=30
            )
        else:
            self._pool = await asyncpg.create_pool(
                host=PG_HOST,
                port=PG_PORT,
                database=PG_DB,
                user=PG_USER,
                password=PG_PASS,
                min_size=1,
                max_size=5,
                command_timeout=30,
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
            import ssl
            import paho.mqtt.client as paho_mqtt

            self._mqtt_client = paho_mqtt.Client()
            if MQTT_USERNAME and MQTT_PASSWORD:
                self._mqtt_client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)
            if MQTT_TLS:
                # Internal EMQX listener is TLS; allow insecure in Docker network.
                self._mqtt_client.tls_set(
                    tls_version=ssl.PROTOCOL_TLS_CLIENT, cert_reqs=ssl.CERT_NONE
                )
                if MQTT_TLS_INSECURE:
                    self._mqtt_client.tls_insecure_set(True)
            self._mqtt_client.connect(MQTT_HOST, MQTT_PORT, keepalive=60)
            self._mqtt_client.loop_start()
            logger.info("mqtt_connected_for_republish")
        except Exception as e:
            logger.warning("mqtt_connect_failed", extra={"error": str(e)})

    async def deliver(self, job: dict):
        """Deliver a single route job."""
        route = job["route"]
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
            republish_topic = republish_topic.replace(
                "{device_id}", payload.get("device_id", "")
            )

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
        route = job.get("route") or {}
        try:
            async with self._pool.acquire() as conn:
                async with conn.transaction():
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
                        route.get("id"),
                        job.get("topic", ""),
                        json.dumps(job.get("payload") or {}, default=str),
                        route.get("destination_type"),
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
                job = None
                try:
                    job = json.loads(msg.data.decode())
                    await self.deliver(job)
                    await msg.ack()
                    self.delivered += 1
                except Exception as e:
                    route_id = None
                    try:
                        route_id = (job or {}).get("route", {}).get("id")
                    except Exception:
                        route_id = None
                    logger.warning(
                        "delivery_failed",
                        extra={"error": str(e), "route_id": route_id},
                    )
                    self.failed += 1

                    metadata = msg.metadata
                    if metadata and metadata.num_delivered >= 3:
                        if job is not None:
                            await self.write_dlq(job, str(e))
                        await msg.term()
                    else:
                        await msg.nak()

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

        logger.info(
            "shutdown_complete",
            extra={"delivered": self.delivered, "failed": self.failed},
        )

    async def run(self):
        await self.init_db()
        await self.init_nats()
        await self.init_mqtt()

        self._workers = []
        for i in range(WORKER_COUNT):
            self._workers.append(asyncio.create_task(self.worker(i)))

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

