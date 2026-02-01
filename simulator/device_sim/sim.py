import json
import os
import random
import time
from datetime import datetime, timezone

import paho.mqtt.client as mqtt

MQTT_HOST = os.getenv("MQTT_HOST", "simcloud-mqtt")
MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))
TENANT = os.getenv("TENANT", "enabled")

SITES = [
    {"site": "MET-GLD", "core_switch": "sw-core-1"},
    {"site": "MET-ANA", "core_switch": "sw-core-1"},
]

CORE_OUTAGE_PERIOD = int(os.getenv("CORE_OUTAGE_PERIOD", "120"))   # seconds
CORE_OUTAGE_DURATION = int(os.getenv("CORE_OUTAGE_DURATION", "30")) # seconds

UPS_OUTAGE_PERIOD = int(os.getenv("UPS_OUTAGE_PERIOD", "180"))
UPS_OUTAGE_DURATION = int(os.getenv("UPS_OUTAGE_DURATION", "45"))

def iso_utc():
    return datetime.now(timezone.utc).isoformat()

def pub(client, topic, payload):
    client.publish(topic, json.dumps(payload), qos=0, retain=False)

def make_ping(site, device_id, up=True, loss=None, rtt_ms=None):
    return {
        "ts": iso_utc(),
        "tenant": TENANT,
        "site": site,
        "layer": "network",
        "entity_type": "device",
        "entity_id": device_id,
        "signal": "ping",
        "metric": "up",
        "value": 1 if up else 0,
        "tags": {"role": "edge" if "cam" in device_id else "core"},
        "extras": {"packet_loss": loss, "rtt_ms": rtt_ms}
    }

def make_ups(site, ups_id="ups-1", on_batt=False, batt_pct=100):
    return {
        "ts": iso_utc(),
        "tenant": TENANT,
        "site": site,
        "layer": "power",
        "entity_type": "device",
        "entity_id": ups_id,
        "signal": "ups",
        "metric": "on_battery",
        "value": 1 if on_batt else 0,
        "extras": {"battery_pct": batt_pct}
    }

def make_temp(site, sensor_id="env-1", temp_c=24.0):
    return {
        "ts": iso_utc(),
        "tenant": TENANT,
        "site": site,
        "layer": "power",
        "entity_type": "device",
        "entity_id": sensor_id,
        "signal": "temp",
        "metric": "temp_c",
        "value": float(temp_c)
    }

def make_service(site, service_id="vms-recording", ok=True, code=200):
    return {
        "ts": iso_utc(),
        "tenant": TENANT,
        "site": site,
        "layer": "service",
        "entity_type": "service",
        "entity_id": service_id,
        "signal": "http",
        "metric": "ok",
        "value": 1 if ok else 0,
        "extras": {"status_code": code}
    }

def in_window(t, period, duration):
    return (t % period) < duration

def main():
    client = mqtt.Client()
    client.connect(MQTT_HOST, MQTT_PORT, keepalive=60)
    client.loop_start()

    per_site_devices = {}
    for s in SITES:
        site = s["site"]
        core = s["core_switch"]
        cams = [f"cam-{i:02d}" for i in range(1, 9)]
        dist = [f"sw-dist-{i}" for i in range(1, 3)]
        per_site_devices[site] = {"core": core, "dist": dist, "cams": cams}

    start = time.time()

    while True:
        now = time.time()
        elapsed = int(now - start)

        for site, inv in per_site_devices.items():
            core = inv["core"]
            dist = inv["dist"]
            cams = inv["cams"]

            # Repeating outages
            core_up = True
            if site == "MET-GLD" and in_window(elapsed, CORE_OUTAGE_PERIOD, CORE_OUTAGE_DURATION):
                core_up = False

            ups_on_batt = False
            batt_pct = 100
            if site == "MET-ANA" and in_window(elapsed, UPS_OUTAGE_PERIOD, UPS_OUTAGE_DURATION):
                ups_on_batt = True
                # simple sawtooth discharge within window
                batt_pct = max(5, 100 - int((elapsed % UPS_OUTAGE_PERIOD) / max(1, UPS_OUTAGE_DURATION/10)))

            # Power/env
            pub(client, f"tenant/{TENANT}/site/{site}/power/ups", make_ups(site, on_batt=ups_on_batt, batt_pct=batt_pct))
            temp = 24.0 + (8.0 if ups_on_batt else 0.0) + random.uniform(-0.3, 0.3)
            pub(client, f"tenant/{TENANT}/site/{site}/power/temp", make_temp(site, temp_c=temp))

            # Network: publish core ping always
            pub(client, f"tenant/{TENANT}/site/{site}/network/ping", make_ping(site, core, up=core_up, loss=0.0 if core_up else 1.0, rtt_ms=1 if core_up else None))

            # Downstream: only publish when core is up (visibility model)
            if core_up:
                for sw in dist:
                    sw_up = (random.random() > 0.02)
                    pub(client, f"tenant/{TENANT}/site/{site}/network/ping", make_ping(site, sw, up=sw_up, loss=0.0 if sw_up else 1.0, rtt_ms=2 if sw_up else None))
                for cam in cams:
                    cam_up = (random.random() > 0.05)
                    pub(client, f"tenant/{TENANT}/site/{site}/network/ping", make_ping(site, cam, up=cam_up, loss=0.0 if cam_up else 1.0, rtt_ms=5 if cam_up else None))

            # Service check: only meaningful when core is up (sim choice)
            svc_ok = True
            code = 200
            if core_up and site == "MET-GLD" and (elapsed % 45) < 10:
                svc_ok = False
                code = 503
            pub(client, f"tenant/{TENANT}/site/{site}/service/http", make_service(site, ok=svc_ok, code=code))

        time.sleep(5)

if __name__ == "__main__":
    main()
