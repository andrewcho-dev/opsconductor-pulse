#!/usr/bin/env python3
"""Seed demo data for Pulse IoT platform."""
import asyncio
import hashlib
import json
import os
import random
import math
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import asyncpg
import httpx

PG_HOST = os.getenv("PG_HOST", "localhost")
PG_PORT = int(os.getenv("PG_PORT", "5432"))
PG_DB = os.getenv("PG_DB", "iotcloud")
PG_USER = os.getenv("PG_USER", "iot")
PG_PASS = os.getenv("PG_PASS", "iot_dev")
INFLUXDB_URL = os.getenv("INFLUXDB_URL", "http://localhost:8181")
INFLUXDB_TOKEN = os.getenv("INFLUXDB_TOKEN", "influx-dev-token-change-me")

TENANTS = ["tenant-a", "tenant-b"]
SITES = {
    "tenant-a": ["warehouse-east", "warehouse-west", "cold-storage-1"],
    "tenant-b": ["factory-floor", "loading-dock", "office-hvac"],
}

RULES_TEMPLATE = [
    {"name": "Low Battery Warning", "metric_name": "battery_pct", "operator": "LT", "threshold": 25.0, "severity": 2, "description": "Battery below 25%"},
    {"name": "Critical Battery", "metric_name": "battery_pct", "operator": "LT", "threshold": 10.0, "severity": 1, "description": "Battery critically low"},
    {"name": "High Temperature", "metric_name": "temp_c", "operator": "GT", "threshold": 35.0, "severity": 3, "description": "Temperature exceeds 35°C"},
    {"name": "Freezing Alert", "metric_name": "temp_c", "operator": "LT", "threshold": 2.0, "severity": 2, "description": "Temperature near freezing"},
    {"name": "Weak Signal", "metric_name": "rssi_dbm", "operator": "LT", "threshold": -85.0, "severity": 4, "description": "Signal strength degraded"},
]


def now_utc():
    return datetime.now(timezone.utc)


def iter_devices():
    for tenant_id in TENANTS:
        for site_id in SITES[tenant_id]:
            for idx in range(1, 6):
                device_id = f"{site_id}-sensor-{idx:02d}"
                yield tenant_id, site_id, device_id


def pick_special_devices(devices):
    random.seed(42)
    stale = set()
    low_battery = set()
    high_temp = set()
    weak_signal = set()
    for tenant_id in TENANTS:
        tenant_devices = [d for d in devices if d[0] == tenant_id]
        stale.update(random.sample(tenant_devices, 2))
        low_battery.update(random.sample(tenant_devices, 2))
        high_temp.update(random.sample(tenant_devices, 1))
        weak_signal.update(random.sample(tenant_devices, 2))
    return stale, low_battery, high_temp, weak_signal


async def seed_device_registry(pool, devices):
    async with pool.acquire() as conn:
        for tenant_id, site_id, device_id in devices:
            token_hash = hashlib.sha256(f"tok-{device_id}".encode()).hexdigest()
            metadata = {
                "model": random.choice(["DHT22", "BME280", "SHT31"]),
                "installed": "2024-01-15",
            }
            await conn.execute(
                """
                INSERT INTO device_registry (tenant_id, device_id, site_id, status, provision_token_hash, fw_version, metadata)
                VALUES ($1,$2,$3,'ACTIVE',$4,$5,$6::jsonb)
                ON CONFLICT (tenant_id, device_id) DO NOTHING
                """,
                tenant_id,
                device_id,
                site_id,
                token_hash,
                random.choice(["1.0.0", "1.1.0", "1.2.3", "2.0.0"]),
                json.dumps(metadata),
            )


async def seed_device_state(pool, devices, stale, low_battery, high_temp, weak_signal):
    now = now_utc()
    stale_time = now - timedelta(minutes=2)
    async with pool.acquire() as conn:
        for tenant_id, site_id, device_id in devices:
            status = "STALE" if (tenant_id, site_id, device_id) in stale else "ONLINE"
            last_ts = stale_time if status == "STALE" else now
            battery = random.uniform(60, 100)
            temp = random.uniform(18, 26)
            rssi = random.uniform(-70, -50)
            humidity = random.uniform(40, 60)

            if (tenant_id, site_id, device_id) in low_battery:
                battery = random.uniform(15, 25)
            if (tenant_id, site_id, device_id) in high_temp:
                temp = random.uniform(32, 38)
            if (tenant_id, site_id, device_id) in weak_signal:
                rssi = random.uniform(-95, -85)

            state = {
                "battery_pct": round(battery, 1),
                "temp_c": round(temp, 1),
                "rssi_dbm": int(rssi),
                "humidity_pct": round(humidity, 1),
            }
            await conn.execute(
                """
                INSERT INTO device_state (
                    tenant_id, site_id, device_id, status,
                    last_heartbeat_at, last_telemetry_at, last_seen_at,
                    state
                )
                VALUES ($1,$2,$3,$4,$5,$6,$7,$8::jsonb)
                ON CONFLICT (tenant_id, device_id) DO UPDATE SET
                    site_id = EXCLUDED.site_id,
                    status = EXCLUDED.status,
                    last_heartbeat_at = EXCLUDED.last_heartbeat_at,
                    last_telemetry_at = EXCLUDED.last_telemetry_at,
                    last_seen_at = EXCLUDED.last_seen_at,
                    state = EXCLUDED.state
                """,
                tenant_id,
                site_id,
                device_id,
                status,
                last_ts,
                last_ts,
                last_ts,
                json.dumps(state),
            )


async def seed_alert_rules(pool):
    rule_ids = {}
    async with pool.acquire() as conn:
        for tenant_id in TENANTS:
            for rule in RULES_TEMPLATE:
                rule_id = str(uuid4())
                await conn.execute(
                    """
                    INSERT INTO alert_rules (
                        tenant_id, rule_id, name, enabled,
                        metric_name, operator, threshold, severity, description
                    )
                    VALUES ($1,$2,$3,true,$4,$5,$6,$7,$8)
                    ON CONFLICT (tenant_id, rule_id) DO NOTHING
                    """,
                    tenant_id,
                    rule_id,
                    rule["name"],
                    rule["metric_name"],
                    rule["operator"],
                    rule["threshold"],
                    rule["severity"],
                    rule["description"],
                )
                rule_ids[(tenant_id, rule["name"])] = rule_id
    return rule_ids


async def seed_fleet_alerts(pool, devices, stale, low_battery, rule_ids):
    now = now_utc()
    async with pool.acquire() as conn:
        for tenant_id, site_id, device_id in devices:
            if (tenant_id, site_id, device_id) in stale:
                await conn.execute(
                    """
                    INSERT INTO fleet_alert (
                        tenant_id, site_id, device_id, alert_type,
                        fingerprint, status, severity, confidence, summary, details
                    )
                    VALUES ($1,$2,$3,'NO_HEARTBEAT',$4,'OPEN',$5,$6,$7,$8::jsonb)
                    ON CONFLICT (tenant_id, fingerprint) WHERE (status='OPEN') DO NOTHING
                    """,
                    tenant_id,
                    site_id,
                    device_id,
                    f"NO_HEARTBEAT:{device_id}",
                    4,
                    0.9,
                    f"Device {device_id} has not sent heartbeat",
                    json.dumps({"last_heartbeat_at": now.isoformat()}),
                )

            if (tenant_id, site_id, device_id) in low_battery:
                battery = random.uniform(15, 24)
                rule_id = rule_ids.get((tenant_id, "Low Battery Warning"))
                await conn.execute(
                    """
                    INSERT INTO fleet_alert (
                        tenant_id, site_id, device_id, alert_type,
                        fingerprint, status, severity, confidence, summary, details
                    )
                    VALUES ($1,$2,$3,'THRESHOLD',$4,'OPEN',$5,$6,$7,$8::jsonb)
                    ON CONFLICT (tenant_id, fingerprint) WHERE (status='OPEN') DO NOTHING
                    """,
                    tenant_id,
                    site_id,
                    device_id,
                    f"RULE:{rule_id}:{device_id}",
                    2,
                    0.8,
                    f"Low Battery Warning: {device_id} battery at {battery:.1f}%",
                    json.dumps({
                        "rule_id": rule_id,
                        "rule_name": "Low Battery Warning",
                        "metric_name": "battery_pct",
                        "metric_value": round(battery, 1),
                        "operator": "LT",
                        "threshold": 25.0,
                    }),
                )


def _line_protocol(device_id, site_id, seq, battery, temp, rssi, humidity, ts_ns):
    return (
        f"telemetry,device_id={device_id},site_id={site_id} "
        f"seq={seq}i,battery_pct={battery:.1f},temp_c={temp:.1f},"
        f"rssi_dbm={int(rssi)}i,humidity_pct={humidity:.1f} {ts_ns}"
    )


def _heartbeat_line(device_id, site_id, seq, ts_ns):
    return f"heartbeat,device_id={device_id},site_id={site_id} seq={seq}i {ts_ns}"


async def write_lines(http_client, db_name, lines):
    if not lines:
        return
    headers = {"Authorization": f"Bearer {INFLUXDB_TOKEN}", "Content-Type": "text/plain"}
    body = "\n".join(lines)
    resp = await http_client.post(f"{INFLUXDB_URL}/api/v3/write_lp?db={db_name}", content=body, headers=headers)
    if resp.status_code >= 300:
        raise RuntimeError(f"InfluxDB write failed: {resp.status_code} {resp.text[:200]}")


async def seed_influxdb(devices):
    start = now_utc() - timedelta(days=7)
    interval = timedelta(minutes=5)
    points_per_device = int((7 * 24 * 60) / 5)
    async with httpx.AsyncClient(timeout=20.0) as client:
        for tenant_id in TENANTS:
            db_name = f"telemetry_{tenant_id}"
            lines = []
            for t_id, site_id, device_id in devices:
                if t_id != tenant_id:
                    continue
                battery = 100.0
                rssi = -65.0
                seq = 0
                ts = start
                for _ in range(points_per_device):
                    seq += 1
                    battery -= 0.5 / 12
                    if battery < 5 or random.random() < 0.005:
                        battery = 100.0
                    daily_phase = (ts.hour + ts.minute / 60) / 24.0
                    temp = 22 + (4 * (1 + math.sin(daily_phase * 2 * math.pi)) / 2) + random.uniform(-2, 2)
                    rssi += random.uniform(-2, 2)
                    rssi = max(-100, min(-30, rssi))
                    humidity = 50 + random.uniform(-10, 10)
                    ts_ns = int(ts.timestamp() * 1_000_000_000)
                    lines.append(_line_protocol(device_id, site_id, seq, battery, temp, rssi, humidity, ts_ns))
                    lines.append(_heartbeat_line(device_id, site_id, seq, ts_ns))
                    if len(lines) >= 5000:
                        await write_lines(client, db_name, lines)
                        lines = []
                    ts += interval
            if lines:
                await write_lines(client, db_name, lines)


async def main():
    devices = list(iter_devices())
    stale, low_battery, high_temp, weak_signal = pick_special_devices(devices)

    print("Connecting to PostgreSQL...")
    pool = await asyncpg.create_pool(
        host=PG_HOST,
        port=PG_PORT,
        database=PG_DB,
        user=PG_USER,
        password=PG_PASS,
        min_size=1,
        max_size=5,
    )

    print("Seeding device_registry...")
    await seed_device_registry(pool, devices)

    print("Seeding device_state...")
    await seed_device_state(pool, devices, stale, low_battery, high_temp, weak_signal)

    print("Seeding alert_rules...")
    rule_ids = await seed_alert_rules(pool)

    print("Seeding fleet_alert...")
    await seed_fleet_alerts(pool, devices, stale, low_battery, rule_ids)

    print("Seeding InfluxDB telemetry (7 days)...")
    await seed_influxdb(devices)

    print("Done!")
    await pool.close()


if __name__ == "__main__":
    asyncio.run(main())
