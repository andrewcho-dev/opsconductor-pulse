"""
MQTT -> NATS bridge (EMQX OSS compatible)

Subscribes to EMQX topics and republishes a normalized envelope into NATS
subjects so that ingest workers only consume from JetStream.
"""

import os
import json
import time
import asyncio
import logging
import signal
import threading

import nats
import paho.mqtt.client as paho_mqtt

logger = logging.getLogger("mqtt_nats_bridge")
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s"
)

NATS_URL = os.getenv("NATS_URL", "nats://localhost:4222")

MQTT_HOST = os.getenv("MQTT_HOST", "localhost")
MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))
MQTT_USERNAME = os.getenv("MQTT_USERNAME")
MQTT_PASSWORD = os.getenv("MQTT_PASSWORD")
MQTT_TOPIC = os.getenv("MQTT_TOPIC", "tenant/+/device/+/+")
MQTT_TLS = os.getenv("MQTT_TLS", "true").lower() == "true"
MQTT_TLS_INSECURE = os.getenv("MQTT_TLS_INSECURE", "true").lower() == "true"


def topic_extract(topic: str) -> tuple[str | None, str | None, str | None]:
    parts = topic.split("/")
    if len(parts) < 5:
        return None, None, None
    if parts[0] != "tenant" or parts[2] != "device":
        return None, None, None
    tenant_id = parts[1]
    device_id = parts[3]
    msg_type = "/".join(parts[4:])
    return tenant_id, device_id, msg_type


class Bridge:
    def __init__(self):
        self._nc = None
        self._js = None
        self._loop = None
        self._shutdown = asyncio.Event()
        self._mqtt = None

    async def init_nats(self):
        self._nc = await nats.connect(NATS_URL)
        self._js = self._nc.jetstream()
        logger.info("nats_connected", extra={"url": NATS_URL})

    def _on_connect(self, client, userdata, flags, rc):
        logger.info("mqtt_connected", extra={"rc": rc, "topic": MQTT_TOPIC})
        client.subscribe(MQTT_TOPIC)

    def _on_message(self, client, userdata, msg):
        try:
            payload = json.loads(msg.payload.decode("utf-8"))
        except Exception:
            logger.warning("mqtt_invalid_json", extra={"topic": msg.topic})
            return

        if "ts" not in payload:
            payload["ts"] = time.time()

        tenant_id, device_id, msg_type = topic_extract(msg.topic)
        if tenant_id is None or device_id is None or msg_type is None:
            return

        if msg_type.startswith("shadow/"):
            subject = f"shadow.{tenant_id}"
        elif msg_type.startswith("commands/"):
            subject = f"commands.{tenant_id}"
        else:
            subject = f"telemetry.{tenant_id}"

        envelope = {
            "topic": msg.topic,
            "tenant_id": tenant_id,
            "device_id": device_id,
            "msg_type": msg_type,
            "username": "",
            "payload": payload,
            "ts": int(time.time() * 1000),
        }

        if self._loop:
            if not self._js:
                logger.warning("jetstream_not_ready")
                return
            asyncio.run_coroutine_threadsafe(
                self._js.publish(
                    subject,
                    json.dumps(envelope, default=str).encode(),
                    timeout=1.0,
                ),
                self._loop,
            )

    def _try_init_mqtt(self) -> bool:
        import ssl

        client = paho_mqtt.Client()
        self._mqtt = client
        if MQTT_USERNAME and MQTT_PASSWORD:
            client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)
        if MQTT_TLS:
            client.tls_set(tls_version=ssl.PROTOCOL_TLS_CLIENT, cert_reqs=ssl.CERT_NONE)
            if MQTT_TLS_INSECURE:
                client.tls_insecure_set(True)
        client.on_connect = self._on_connect
        client.on_message = self._on_message
        try:
            client.connect(MQTT_HOST, MQTT_PORT, keepalive=60)
            client.loop_start()
            return True
        except Exception as e:
            logger.warning("mqtt_connect_failed: %s", e)
            try:
                client.loop_stop()
                client.disconnect()
            except Exception:
                pass
            self._mqtt = None
            return False

    async def shutdown(self):
        logger.info("shutdown_initiated")
        self._shutdown.set()
        if self._mqtt:
            self._mqtt.loop_stop()
            self._mqtt.disconnect()
        if self._nc:
            await self._nc.drain()
        logger.info("shutdown_complete")

    async def run(self):
        self._loop = asyncio.get_running_loop()
        await self.init_nats()

        # MQTT may not be ready when the container starts; keep retrying.
        while not self._shutdown.is_set():
            if self._try_init_mqtt():
                break
            await asyncio.sleep(1.0)

        for sig in (signal.SIGTERM, signal.SIGINT):
            self._loop.add_signal_handler(sig, self._shutdown.set)
        await self._shutdown.wait()
        await self.shutdown()


async def main():
    bridge = Bridge()
    await bridge.run()


if __name__ == "__main__":
    asyncio.run(main())

