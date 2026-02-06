# Phase 26.1: Create Device Simulator Script

## Task

Create `scripts/device_simulator.py` that continuously sends telemetry via HTTP POST to the new ingestion endpoint.

## Requirements

### Configuration
```python
import os

# Target endpoint (use HTTP ingestion from Phase 23)
INGEST_URL = os.getenv("INGEST_URL", "http://iot-ui:8080")

# Simulation parameters
NUM_DEVICES_PER_TENANT = int(os.getenv("NUM_DEVICES_PER_TENANT", "5"))
HEARTBEAT_INTERVAL = int(os.getenv("HEARTBEAT_INTERVAL", "30"))  # seconds
TELEMETRY_INTERVAL = int(os.getenv("TELEMETRY_INTERVAL", "10"))  # seconds

# Tenants and sites to simulate
TENANTS = {
    "tenant-a": {
        "sites": ["warehouse-east", "warehouse-west", "cold-storage-1"],
        "token_prefix": "tok-tenant-a",
    },
    "tenant-b": {
        "sites": ["factory-floor", "loading-dock", "office-hvac"],
        "token_prefix": "tok-tenant-b",
    },
}
```

### Device State Model

Each simulated device maintains state that evolves over time:

```python
@dataclass
class SimulatedDevice:
    tenant_id: str
    device_id: str
    site_id: str
    token: str

    # Evolving state
    battery_pct: float = 100.0
    temp_c: float = 22.0
    rssi_dbm: int = -65
    humidity_pct: float = 50.0
    seq: int = 0

    def tick(self):
        """Update state with realistic variation."""
        self.seq += 1

        # Battery slowly drains, occasionally "recharges"
        self.battery_pct -= random.uniform(0.01, 0.05)
        if self.battery_pct < 20 and random.random() < 0.1:
            self.battery_pct = 100.0  # Simulated recharge
        self.battery_pct = max(5.0, min(100.0, self.battery_pct))

        # Temperature fluctuates with daily cycle + noise
        hour = datetime.now().hour
        daily_cycle = 3 * math.sin(2 * math.pi * hour / 24)  # ±3°C daily swing
        self.temp_c = 22.0 + daily_cycle + random.uniform(-1, 1)

        # RSSI random walk
        self.rssi_dbm += random.randint(-2, 2)
        self.rssi_dbm = max(-95, min(-40, self.rssi_dbm))

        # Humidity fluctuates
        self.humidity_pct += random.uniform(-2, 2)
        self.humidity_pct = max(30, min(80, self.humidity_pct))

    def get_telemetry_payload(self) -> dict:
        return {
            "ts": datetime.now(timezone.utc).isoformat(),
            "site_id": self.site_id,
            "seq": self.seq,
            "metrics": {
                "battery_pct": round(self.battery_pct, 1),
                "temp_c": round(self.temp_c, 1),
                "rssi_dbm": self.rssi_dbm,
                "humidity_pct": round(self.humidity_pct, 1),
            }
        }

    def get_heartbeat_payload(self) -> dict:
        return {
            "ts": datetime.now(timezone.utc).isoformat(),
            "site_id": self.site_id,
            "seq": self.seq,
        }
```

### Main Loop

```python
import asyncio
import httpx
import random
import math
from datetime import datetime, timezone
from dataclasses import dataclass

async def send_telemetry(client: httpx.AsyncClient, device: SimulatedDevice):
    """Send telemetry via HTTP POST."""
    url = f"{INGEST_URL}/ingest/v1/tenant/{device.tenant_id}/device/{device.device_id}/telemetry"
    headers = {
        "Content-Type": "application/json",
        "X-Provision-Token": device.token,
    }
    payload = device.get_telemetry_payload()

    try:
        resp = await client.post(url, json=payload, headers=headers)
        if resp.status_code == 202:
            print(f"[telemetry] {device.device_id} seq={device.seq} battery={payload['metrics']['battery_pct']}%")
        else:
            print(f"[telemetry] {device.device_id} FAILED: {resp.status_code} {resp.text[:100]}")
    except Exception as e:
        print(f"[telemetry] {device.device_id} ERROR: {e}")

async def send_heartbeat(client: httpx.AsyncClient, device: SimulatedDevice):
    """Send heartbeat via HTTP POST."""
    url = f"{INGEST_URL}/ingest/v1/tenant/{device.tenant_id}/device/{device.device_id}/heartbeat"
    headers = {
        "Content-Type": "application/json",
        "X-Provision-Token": device.token,
    }
    payload = device.get_heartbeat_payload()

    try:
        resp = await client.post(url, json=payload, headers=headers)
        if resp.status_code == 202:
            print(f"[heartbeat] {device.device_id} seq={device.seq}")
        else:
            print(f"[heartbeat] {device.device_id} FAILED: {resp.status_code}")
    except Exception as e:
        print(f"[heartbeat] {device.device_id} ERROR: {e}")

def create_devices() -> list[SimulatedDevice]:
    """Create simulated devices for all tenants."""
    devices = []
    for tenant_id, config in TENANTS.items():
        for site_id in config["sites"]:
            for i in range(NUM_DEVICES_PER_TENANT):
                device_id = f"{site_id}-sim-{i+1:02d}"
                token = f"{config['token_prefix']}-{device_id}"
                devices.append(SimulatedDevice(
                    tenant_id=tenant_id,
                    device_id=device_id,
                    site_id=site_id,
                    token=token,
                    battery_pct=random.uniform(60, 100),
                    temp_c=random.uniform(18, 26),
                    rssi_dbm=random.randint(-75, -50),
                    humidity_pct=random.uniform(40, 60),
                ))
    return devices

async def telemetry_loop(client: httpx.AsyncClient, devices: list[SimulatedDevice]):
    """Send telemetry for all devices periodically."""
    while True:
        for device in devices:
            device.tick()
            await send_telemetry(client, device)
            await asyncio.sleep(0.05)  # Small delay between devices
        await asyncio.sleep(TELEMETRY_INTERVAL)

async def heartbeat_loop(client: httpx.AsyncClient, devices: list[SimulatedDevice]):
    """Send heartbeats for all devices periodically."""
    while True:
        for device in devices:
            await send_heartbeat(client, device)
            await asyncio.sleep(0.02)
        await asyncio.sleep(HEARTBEAT_INTERVAL)

async def main():
    print(f"Device Simulator starting...")
    print(f"  INGEST_URL: {INGEST_URL}")
    print(f"  Tenants: {list(TENANTS.keys())}")
    print(f"  Devices per tenant: {NUM_DEVICES_PER_TENANT * len(list(TENANTS.values())[0]['sites'])}")
    print(f"  Telemetry interval: {TELEMETRY_INTERVAL}s")
    print(f"  Heartbeat interval: {HEARTBEAT_INTERVAL}s")

    devices = create_devices()
    print(f"  Total devices: {len(devices)}")

    # Register devices first (they need to exist in device_registry)
    await register_devices(devices)

    async with httpx.AsyncClient(timeout=10.0) as client:
        await asyncio.gather(
            telemetry_loop(client, devices),
            heartbeat_loop(client, devices),
        )

async def register_devices(devices: list[SimulatedDevice]):
    """Ensure devices exist in device_registry with correct tokens."""
    import asyncpg
    import hashlib

    PG_HOST = os.getenv("PG_HOST", "iot-postgres")
    PG_PORT = int(os.getenv("PG_PORT", "5432"))
    PG_DB = os.getenv("PG_DB", "iotcloud")
    PG_USER = os.getenv("PG_USER", "iot")
    PG_PASS = os.getenv("PG_PASS", "iot_dev")

    pool = await asyncpg.create_pool(
        host=PG_HOST, port=PG_PORT, database=PG_DB,
        user=PG_USER, password=PG_PASS,
        min_size=1, max_size=2
    )

    async with pool.acquire() as conn:
        for device in devices:
            token_hash = hashlib.sha256(device.token.encode()).hexdigest()
            await conn.execute("""
                INSERT INTO device_registry (tenant_id, device_id, site_id, status, provision_token_hash)
                VALUES ($1, $2, $3, 'ACTIVE', $4)
                ON CONFLICT (tenant_id, device_id) DO UPDATE SET
                    provision_token_hash = $4,
                    status = 'ACTIVE'
            """, device.tenant_id, device.device_id, device.site_id, token_hash)

    await pool.close()
    print(f"Registered {len(devices)} devices")

if __name__ == "__main__":
    asyncio.run(main())
```

## Verification

```bash
# Run locally (needs port forwarding)
cd /home/opsconductor/simcloud
INGEST_URL=http://localhost:8080 python3 scripts/device_simulator.py

# Should see output like:
# [telemetry] warehouse-east-sim-01 seq=1 battery=95.3%
# [heartbeat] warehouse-east-sim-01 seq=1
```

## Files

| Action | File |
|--------|------|
| CREATE | `scripts/device_simulator.py` |
