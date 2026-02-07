import asyncio
import json
import os
import random
import time
import urllib.request
import urllib.error

import paho.mqtt.client as mqtt

from sensor_profiles import parse_profile_mix, pick_profile_by_mix

MQTT_HOST = os.getenv("MQTT_HOST", "iot-mqtt")
MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))

TENANT_ID = os.getenv("TENANT_ID", "enabled")
SITE_PREFIX = os.getenv("SITE_PREFIX", "sim-site")
SITES_COUNT = int(os.getenv("SITES_COUNT", "5"))
DEVICE_COUNT = int(os.getenv("DEVICE_COUNT", "100"))

PROVISION_API_URL = os.getenv("PROVISION_API_URL", "")
PROVISION_ADMIN_KEY = os.getenv("PROVISION_ADMIN_KEY", "")

SENSOR_PROFILE_MIX = os.getenv("SENSOR_PROFILE_MIX", "")
INTERVAL_JITTER_PCT = float(os.getenv("INTERVAL_JITTER_PCT", "0.1"))

BATTERY_FLOOR = float(os.getenv("BATTERY_FLOOR", "10"))
BATTERY_DRAIN_MEAN = float(os.getenv("BATTERY_DRAIN_MEAN", "0.02"))
BATTERY_DRAIN_JITTER = float(os.getenv("BATTERY_DRAIN_JITTER", "0.02"))
RECHARGE_CHANCE = float(os.getenv("RECHARGE_CHANCE", "0.002"))
RECHARGE_BOOST_MIN = float(os.getenv("RECHARGE_BOOST_MIN", "5"))
RECHARGE_BOOST_MAX = float(os.getenv("RECHARGE_BOOST_MAX", "15"))

FAILURE_DOWNTIME_MIN_SECONDS = int(os.getenv("FAILURE_DOWNTIME_MIN_SECONDS", "30"))
FAILURE_DOWNTIME_MAX_SECONDS = int(os.getenv("FAILURE_DOWNTIME_MAX_SECONDS", "300"))

LOG_STATS_SECONDS = int(os.getenv("LOG_STATS_SECONDS", "30"))


def clamp(v, lo, hi):
    return max(lo, min(hi, v))


def jitter(interval):
    if interval <= 0:
        return 1.0
    delta = interval * INTERVAL_JITTER_PCT
    return max(1.0, interval + random.uniform(-delta, delta))


def build_topic(device_id, msg_type):
    return f"tenant/{TENANT_ID}/device/{device_id}/{msg_type}"


def generate_devices():
    rng = random.Random(42)
    mix = parse_profile_mix(SENSOR_PROFILE_MIX)
    devices = []
    for idx in range(1, DEVICE_COUNT + 1):
        site_id = f"{SITE_PREFIX}-{(idx % SITES_COUNT) + 1}"
        device_id = f"{site_id}-dev-{idx:05d}"
        profile = pick_profile_by_mix(mix, rng)
        devices.append({"device_id": device_id, "site_id": site_id, "profile": profile})
    return devices


def init_metrics(profile):
    metrics = {}
    for name, cfg in profile["metrics"].items():
        kind = cfg.get("kind", "float")
        if kind == "bool":
            metrics[name] = 1 if random.random() < cfg.get("flip_chance", 0.1) else 0
        elif kind == "counter":
            metrics[name] = round(random.uniform(cfg["min"], cfg["min"] + 10.0), 2)
        elif kind == "enum":
            metrics[name] = random.choice(cfg.get("values", ["off"]))
        else:
            if kind == "int":
                metrics[name] = int(random.uniform(cfg["min"], cfg["max"]))
            else:
                metrics[name] = round(random.uniform(cfg["min"], cfg["max"]), 3)
    if profile.get("battery_powered"):
        metrics["battery_pct"] = round(random.uniform(60.0, 100.0), 2)
    return metrics


def update_metrics(profile, metrics):
    for name, cfg in profile["metrics"].items():
        kind = cfg.get("kind", "float")
        if kind == "bool":
            if random.random() < cfg.get("flip_chance", 0.05):
                metrics[name] = 0 if metrics.get(name, 0) else 1
        elif kind == "counter":
            step = random.uniform(cfg.get("step_min", 0), cfg.get("step_max", 1))
            metrics[name] = round(metrics.get(name, 0.0) + step, 3)
        elif kind == "enum":
            if random.random() < cfg.get("change_chance", 0.02):
                metrics[name] = random.choice(cfg.get("values", ["off"]))
        else:
            drift = cfg.get("drift", (cfg["max"] - cfg["min"]) * 0.02)
            delta = random.uniform(-drift, drift)
            prev = float(metrics.get(name, (cfg["min"] + cfg["max"]) / 2))
            next_val = clamp(prev + delta, cfg["min"], cfg["max"])
            if kind == "int":
                metrics[name] = int(round(next_val))
            else:
                metrics[name] = round(next_val, 3)

    if profile.get("battery_powered"):
        drain = random.uniform(
            max(0.0, BATTERY_DRAIN_MEAN - BATTERY_DRAIN_JITTER),
            BATTERY_DRAIN_MEAN + BATTERY_DRAIN_JITTER,
        )
        metrics["battery_pct"] = clamp(metrics.get("battery_pct", 100.0) - drain, BATTERY_FLOOR, 100.0)
        if random.random() < RECHARGE_CHANCE:
            metrics["battery_pct"] = clamp(
                metrics["battery_pct"] + random.uniform(RECHARGE_BOOST_MIN, RECHARGE_BOOST_MAX),
                BATTERY_FLOOR,
                100.0,
            )


def provision_device(api_url, admin_key, tenant_id, device_id, site_id):
    payload = json.dumps({"tenant_id": tenant_id, "device_id": device_id, "site_id": site_id}).encode()
    req = urllib.request.Request(
        f"{api_url.rstrip('/')}/api/admin/devices",
        data=payload,
        headers={"Content-Type": "application/json", "X-Admin-Key": admin_key},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        body = json.loads(resp.read().decode())
    activation_code = body["activation_code"]
    activate_payload = json.dumps(
        {"tenant_id": tenant_id, "device_id": device_id, "activation_code": activation_code}
    ).encode()
    activate_req = urllib.request.Request(
        f"{api_url.rstrip('/')}/api/device/activate",
        data=activate_payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(activate_req, timeout=10) as resp:
        activate_body = json.loads(resp.read().decode())
    return activate_body["provision_token"]


def bulk_provision(devices):
    if not PROVISION_API_URL or not PROVISION_ADMIN_KEY:
        return {}
    tokens = {}
    for d in devices:
        try:
            token = provision_device(PROVISION_API_URL, PROVISION_ADMIN_KEY, TENANT_ID, d["device_id"], d["site_id"])
            tokens[d["device_id"]] = token
        except Exception:
            continue
    return tokens


async def device_loop(device, client, token_map, stats):
    profile = device["profile"]
    metrics = init_metrics(profile)
    seq = 0
    online = True
    offline_until = 0.0
    next_hb = time.time() + jitter(profile["heartbeat_interval_seconds"])
    next_tel = time.time() + jitter(profile["telemetry_interval_seconds"])

    while True:
        now = time.time()
        if not online and now >= offline_until:
            online = True

        if online and now >= next_tel:
            if random.random() < profile["failure_probability"]:
                online = False
                offline_until = now + random.uniform(
                    FAILURE_DOWNTIME_MIN_SECONDS, FAILURE_DOWNTIME_MAX_SECONDS
                )
            else:
                seq += 1
                update_metrics(profile, metrics)
                payload = {
                    "tenant_id": TENANT_ID,
                    "site_id": device["site_id"],
                    "device_id": device["device_id"],
                    "msg_type": "telemetry",
                    "seq": seq,
                    "provision_token": token_map.get(device["device_id"], f"tok-{device['device_id']}"),
                    "metrics": metrics,
                }
                try:
                    client.publish(build_topic(device["device_id"], "telemetry"), json.dumps(payload), qos=0)
                    async with stats["lock"]:
                        stats["messages_sent"] += 1
                except Exception:
                    async with stats["lock"]:
                        stats["errors"] += 1
            next_tel = now + jitter(profile["telemetry_interval_seconds"])

        if online and now >= next_hb:
            seq += 1
            payload = {
                "tenant_id": TENANT_ID,
                "site_id": device["site_id"],
                "device_id": device["device_id"],
                "msg_type": "heartbeat",
                "seq": seq,
                "provision_token": token_map.get(device["device_id"], f"tok-{device['device_id']}"),
            }
            try:
                client.publish(build_topic(device["device_id"], "heartbeat"), json.dumps(payload), qos=0)
                async with stats["lock"]:
                    stats["messages_sent"] += 1
            except Exception:
                async with stats["lock"]:
                    stats["errors"] += 1
            next_hb = now + jitter(profile["heartbeat_interval_seconds"])

        await asyncio.sleep(0.2)


async def stats_loop(stats, device_count):
    last_sent = 0
    last_time = time.time()
    while True:
        await asyncio.sleep(LOG_STATS_SECONDS)
        async with stats["lock"]:
            sent = stats["messages_sent"]
            errors = stats["errors"]
        now = time.time()
        rate = (sent - last_sent) / max(1.0, now - last_time)
        last_sent = sent
        last_time = now
        print(
            f"[sim] devices={device_count} msgs_total={sent} msgs_per_sec={rate:.1f} errors={errors}"
        )


async def main():
    devices = generate_devices()
    print(f"[sim] starting with {len(devices)} devices across {SITES_COUNT} sites")

    token_map = bulk_provision(devices)
    if token_map:
        print(f"[sim] provisioned {len(token_map)} devices")
    else:
        print("[sim] provisioning skipped or failed; using deterministic tokens")

    client = mqtt.Client()
    client.connect(MQTT_HOST, MQTT_PORT, keepalive=60)
    client.loop_start()

    stats = {"messages_sent": 0, "errors": 0, "lock": asyncio.Lock()}
    tasks = [device_loop(d, client, token_map, stats) for d in devices]
    tasks.append(stats_loop(stats, len(devices)))
    await asyncio.gather(*tasks)


if __name__ == "__main__":
    asyncio.run(main())
