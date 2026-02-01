import json
import os
import random
import time
from datetime import datetime, timezone
import paho.mqtt.client as mqtt

MQTT_HOST = os.getenv("MQTT_HOST", "iot-mqtt")
MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))

TENANT_ID = os.getenv("TENANT_ID", "enabled")
SITE_ID = os.getenv("SITE_ID", "lab-1")

DEVICE_COUNT = int(os.getenv("DEVICE_COUNT", "25"))
HEARTBEAT_SECONDS = int(os.getenv("HEARTBEAT_SECONDS", "5"))
TELEMETRY_SECONDS = int(os.getenv("TELEMETRY_SECONDS", "10"))

UPLINK_DROP_PERIOD = int(os.getenv("UPLINK_DROP_PERIOD", "60"))
UPLINK_DROP_DURATION = int(os.getenv("UPLINK_DROP_DURATION", "20"))

# Battery realism knobs (dev-friendly)
BATTERY_FLOOR = float(os.getenv("BATTERY_FLOOR", "10"))         # never drop below this (unless you want dead devices later)
DRAIN_PER_TELEM_MEAN = float(os.getenv("DRAIN_PER_TELEM_MEAN", "0.02"))  # percent points per telemetry tick (avg)
DRAIN_PER_TELEM_JITTER = float(os.getenv("DRAIN_PER_TELEM_JITTER", "0.02"))

# Occasional recharge behavior
RECHARGE_CHANCE_PER_TELEM = float(os.getenv("RECHARGE_CHANCE_PER_TELEM", "0.002"))  # ~0.2% per device per telemetry tick
RECHARGE_BOOST_MIN = float(os.getenv("RECHARGE_BOOST_MIN", "5"))
RECHARGE_BOOST_MAX = float(os.getenv("RECHARGE_BOOST_MAX", "15"))

def ts():
    return datetime.now(timezone.utc).isoformat()

def topic(device_id: str, msg_type: str):
    return f"tenant/{TENANT_ID}/device/{device_id}/{msg_type}"

def provision_token(device_id: str) -> str:
    return f"tok-{device_id}"

def publish(client, t, payload):
    client.publish(t, json.dumps(payload), qos=0, retain=False)

def in_drop_window(elapsed):
    return (elapsed % UPLINK_DROP_PERIOD) < UPLINK_DROP_DURATION

def clamp(v, lo, hi):
    return max(lo, min(hi, v))

def main():
    client = mqtt.Client()
    client.connect(MQTT_HOST, MQTT_PORT, keepalive=60)
    client.loop_start()

    devices = []
    for i in range(1, DEVICE_COUNT + 1):
        device_id = f"dev-{i:04d}"
        devices.append({
            "device_id": device_id,
            "battery_pct": random.uniform(70.0, 100.0),
            "temp_c": random.uniform(20.0, 30.0),
            "rssi_dbm": random.randint(-115, -65),
            "snr_db": random.uniform(-8.0, 18.0),
        })

    start = time.time()
    last_hb = 0.0
    last_tel = 0.0

    while True:
        elapsed = int(time.time() - start)
        uplink_drop = in_drop_window(elapsed)
        now = time.time()

        if now - last_hb >= HEARTBEAT_SECONDS:
            last_hb = now
            if not uplink_drop:
                for d in devices:
                    device_id = d["device_id"]
                    payload = {
                        "ts": ts(),
                        "tenant_id": TENANT_ID,
                        "site_id": SITE_ID,
                        "device_id": device_id,
                        "msg_type": "heartbeat",
                        "seq": elapsed,
                        "provision_token": provision_token(device_id),
                    }
                    publish(client, topic(device_id, "heartbeat"), payload)

        if now - last_tel >= TELEMETRY_SECONDS:
            last_tel = now
            if not uplink_drop:
                for d in devices:
                    device_id = d["device_id"]

                    # Battery drain: small, noisy
                    drain = random.uniform(
                        max(0.0, DRAIN_PER_TELEM_MEAN - DRAIN_PER_TELEM_JITTER),
                        DRAIN_PER_TELEM_MEAN + DRAIN_PER_TELEM_JITTER
                    )
                    d["battery_pct"] = d["battery_pct"] - drain

                    # Occasional recharge event (simulates maintenance or charging)
                    if random.random() < RECHARGE_CHANCE_PER_TELEM:
                        boost = random.uniform(RECHARGE_BOOST_MIN, RECHARGE_BOOST_MAX)
                        d["battery_pct"] = d["battery_pct"] + boost

                    d["battery_pct"] = clamp(d["battery_pct"], BATTERY_FLOOR, 100.0)

                    # Temp drift
                    d["temp_c"] = clamp(d["temp_c"] + random.uniform(-0.25, 0.25), 10.0, 45.0)

                    # Signal drift
                    d["rssi_dbm"] = int(clamp(d["rssi_dbm"] + random.randint(-2, 2), -125, -50))
                    d["snr_db"] = float(clamp(d["snr_db"] + random.uniform(-0.7, 0.7), -20.0, 30.0))

                    payload = {
                        "ts": ts(),
                        "tenant_id": TENANT_ID,
                        "site_id": SITE_ID,
                        "device_id": device_id,
                        "msg_type": "telemetry",
                        "seq": elapsed,
                        "provision_token": provision_token(device_id),
                        "metrics": {
                            "battery_pct": round(d["battery_pct"], 2),
                            "temp_c": round(d["temp_c"], 2),
                            "rssi_dbm": d["rssi_dbm"],
                            "snr_db": round(d["snr_db"], 2),
                            "uplink_ok": True
                        }
                    }
                    publish(client, topic(device_id, "telemetry"), payload)

        time.sleep(1)

if __name__ == "__main__":
    main()
