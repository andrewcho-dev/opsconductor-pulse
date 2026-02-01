import asyncio
import json
import os
from datetime import datetime, timezone
from dateutil import parser as dtparser
import asyncpg
import paho.mqtt.client as mqtt

MQTT_HOST = os.getenv("MQTT_HOST", "simcloud-mqtt")
MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))
MQTT_TOPIC = os.getenv("MQTT_TOPIC", "tenant/+/site/+/+")  # subscribe wide by default

PG_HOST = os.getenv("PG_HOST", "simcloud-postgres")
PG_PORT = int(os.getenv("PG_PORT", "5432"))
PG_DB   = os.getenv("PG_DB", "opsconductor")
PG_USER = os.getenv("PG_USER", "opsconductor")
PG_PASS = os.getenv("PG_PASS", "opsconductor_dev")

def utcnow():
    return datetime.now(timezone.utc)

def safe_get(d, k):
    v = d.get(k)
    return v if isinstance(v, str) else None

def parse_event_ts(payload: dict):
    ts = payload.get("ts")
    if isinstance(ts, str):
        try:
            return dtparser.isoparse(ts)
        except Exception:
            return None
    return None

def topic_extract(topic: str):
    # expected: tenant/<tenant>/site/<site>/<rest...>
    parts = topic.split("/")
    tenant = site = None
    if len(parts) >= 4 and parts[0] == "tenant" and parts[2] == "site":
        tenant = parts[1]
        site = parts[3]
    return tenant, site

class Ingestor:
    def __init__(self):
        self.pool = None
        self.queue = asyncio.Queue(maxsize=5000)

    async def init_db(self):
        self.pool = await asyncpg.create_pool(
            host=PG_HOST, port=PG_PORT, database=PG_DB, user=PG_USER, password=PG_PASS,
            min_size=1, max_size=5
        )

    async def db_worker(self):
        while True:
            topic, payload = await self.queue.get()
            try:
                tenant, site = topic_extract(topic)
                layer = safe_get(payload, "layer")
                entity_type = safe_get(payload, "entity_type")
                entity_id = safe_get(payload, "entity_id")
                signal = safe_get(payload, "signal")
                event_ts = parse_event_ts(payload)

                async with self.pool.acquire() as conn:
                    await conn.execute(
                        """
                        INSERT INTO raw_events (event_ts, topic, tenant, site, layer, entity_type, entity_id, signal, payload)
                        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9::jsonb)
                        """,
                        event_ts, topic, tenant, site, layer, entity_type, entity_id, signal, json.dumps(payload)
                    )
            except Exception as e:
                # keep it simple: log and continue
                print(f"[db_worker] insert failed: {e}")
            finally:
                self.queue.task_done()

    def on_connect(self, client, userdata, flags, rc):
        print(f"[mqtt] connected rc={rc}, subscribing to {MQTT_TOPIC}")
        client.subscribe(MQTT_TOPIC)

    def on_message(self, client, userdata, msg):
        try:
            payload = json.loads(msg.payload.decode("utf-8"))
            # Ensure ts exists (sim may send, but enforce anyway)
            if "ts" not in payload:
                payload["ts"] = utcnow().isoformat()
        except Exception:
            payload = {"ts": utcnow().isoformat(), "parse_error": True, "raw": msg.payload.decode("utf-8", errors="replace")}

        try:
            self.queue.put_nowait((msg.topic, payload))
        except asyncio.QueueFull:
            print("[mqtt] queue full, dropping message")

    async def run(self):
        await self.init_db()
        asyncio.create_task(self.db_worker())

        client = mqtt.Client()
        client.on_connect = self.on_connect
        client.on_message = self.on_message
        client.connect(MQTT_HOST, MQTT_PORT, keepalive=60)
        client.loop_start()

        # keep alive
        while True:
            await asyncio.sleep(5)

async def main():
    ing = Ingestor()
    await ing.run()

if __name__ == "__main__":
    asyncio.run(main())
