#!/usr/bin/env python3
"""Initialize InfluxDB databases for all existing tenants.

Reads distinct tenant_id values from device_registry in PostgreSQL,
then writes a dummy point to InfluxDB for each tenant to auto-create
the telemetry_{tenant_id} database.

Usage:
    python scripts/init_influxdb_tenants.py

Environment variables:
    PG_HOST, PG_PORT, PG_DB, PG_USER, PG_PASS - PostgreSQL connection
    INFLUXDB_URL - InfluxDB HTTP URL (default: http://localhost:8181)
    INFLUXDB_TOKEN - InfluxDB auth token
"""
import asyncio
import os
import asyncpg
import httpx


PG_HOST = os.getenv("PG_HOST", "localhost")
PG_PORT = int(os.getenv("PG_PORT", "5432"))
PG_DB = os.getenv("PG_DB", "iotcloud")
PG_USER = os.getenv("PG_USER", "iot")
PG_PASS = os.getenv("PG_PASS", "iot_dev")

INFLUXDB_URL = os.getenv("INFLUXDB_URL", "http://localhost:8181")
INFLUXDB_TOKEN = os.getenv("INFLUXDB_TOKEN", "influx-dev-token-change-me")


async def main():
    conn = await asyncpg.connect(
        host=PG_HOST, port=PG_PORT, database=PG_DB,
        user=PG_USER, password=PG_PASS,
    )

    rows = await conn.fetch("SELECT DISTINCT tenant_id FROM device_registry")
    await conn.close()

    if not rows:
        print("No tenants found in device_registry")
        return

    async with httpx.AsyncClient(timeout=10.0) as client:
        for row in rows:
            tenant_id = row["tenant_id"]
            db_name = f"telemetry_{tenant_id}"

            # Write a dummy init point to auto-create the database
            # This point uses a special _init measurement that won't interfere with real data
            line = f"_init,source=provisioning value=1i"

            try:
                resp = await client.post(
                    f"{INFLUXDB_URL}/api/v3/write_lp?db={db_name}",
                    content=line,
                    headers={
                        "Authorization": f"Bearer {INFLUXDB_TOKEN}",
                        "Content-Type": "text/plain",
                    },
                )
                if resp.status_code < 300:
                    print(f"  OK  telemetry_{tenant_id}")
                else:
                    print(f"  WARN telemetry_{tenant_id}: HTTP {resp.status_code} {resp.text}")
            except Exception as e:
                print(f"  ERR  telemetry_{tenant_id}: {e}")

    print("Done.")


if __name__ == "__main__":
    asyncio.run(main())
