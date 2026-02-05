import asyncio
import json
import os
from datetime import datetime, timezone
import asyncpg
import httpx
from dateutil import parser as dtparser

PG_HOST = os.getenv("PG_HOST", "iot-postgres")
PG_PORT = int(os.getenv("PG_PORT", "5432"))
PG_DB   = os.getenv("PG_DB", "iotcloud")
PG_USER = os.getenv("PG_USER", "iot")
PG_PASS = os.getenv("PG_PASS", "iot_dev")

POLL_SECONDS = int(os.getenv("POLL_SECONDS", "5"))
HEARTBEAT_STALE_SECONDS = int(os.getenv("HEARTBEAT_STALE_SECONDS", "30"))
INFLUXDB_URL = os.getenv("INFLUXDB_URL", "http://iot-influxdb:8181")
INFLUXDB_TOKEN = os.getenv("INFLUXDB_TOKEN", "influx-dev-token-change-me")

DDL = """
CREATE TABLE IF NOT EXISTS device_state (
  tenant_id            TEXT NOT NULL,
  site_id              TEXT NOT NULL,
  device_id            TEXT NOT NULL,
  status               TEXT NOT NULL, -- ONLINE|STALE
  last_heartbeat_at    TIMESTAMPTZ NULL,
  last_telemetry_at    TIMESTAMPTZ NULL,
  last_seen_at         TIMESTAMPTZ NULL,
  last_state_change_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  state                JSONB NOT NULL DEFAULT '{}'::jsonb,
  PRIMARY KEY (tenant_id, device_id)
);

CREATE TABLE IF NOT EXISTS fleet_alert (
  id          BIGSERIAL PRIMARY KEY,
  created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
  closed_at   TIMESTAMPTZ NULL,
  tenant_id   TEXT NOT NULL,
  site_id     TEXT NOT NULL,
  device_id   TEXT NOT NULL,
  alert_type  TEXT NOT NULL,
  fingerprint TEXT NOT NULL,
  status      TEXT NOT NULL DEFAULT 'OPEN',
  severity    INT NOT NULL,
  confidence  REAL NOT NULL,
  summary     TEXT NOT NULL,
  details     JSONB NOT NULL DEFAULT '{}'::jsonb
);

CREATE UNIQUE INDEX IF NOT EXISTS fleet_alert_open_uq
ON fleet_alert (tenant_id, fingerprint)
WHERE status='OPEN';

CREATE INDEX IF NOT EXISTS device_state_site_idx ON device_state (site_id);
CREATE INDEX IF NOT EXISTS fleet_alert_site_idx ON fleet_alert (site_id, status);

CREATE TABLE IF NOT EXISTS alert_rules (
  tenant_id       TEXT NOT NULL,
  rule_id         TEXT NOT NULL DEFAULT gen_random_uuid()::text,
  name            TEXT NOT NULL,
  enabled         BOOLEAN NOT NULL DEFAULT true,
  metric_name     TEXT NOT NULL,
  operator        TEXT NOT NULL,
  threshold       DOUBLE PRECISION NOT NULL,
  severity        INT NOT NULL DEFAULT 3,
  description     TEXT NULL,
  site_ids        TEXT[] NULL,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (tenant_id, rule_id)
);

CREATE INDEX IF NOT EXISTS alert_rules_tenant_idx ON alert_rules (tenant_id, enabled);
"""

def now_utc():
    return datetime.now(timezone.utc)

async def ensure_schema(conn):
    for stmt in DDL.strip().split(";"):
        s = stmt.strip()
        if s:
            await conn.execute(s + ";")

async def open_or_update_alert(conn, tenant_id, site_id, device_id, alert_type, fingerprint, severity, confidence, summary, details):
    await conn.execute(
        """
        INSERT INTO fleet_alert (tenant_id, site_id, device_id, alert_type, fingerprint, status, severity, confidence, summary, details)
        VALUES ($1,$2,$3,$4,$5,'OPEN',$6,$7,$8,$9::jsonb)
        ON CONFLICT (tenant_id, fingerprint) WHERE (status='OPEN')
        DO UPDATE SET
          severity = EXCLUDED.severity,
          confidence = EXCLUDED.confidence,
          summary = EXCLUDED.summary,
          details = EXCLUDED.details
        """,
        tenant_id, site_id, device_id, alert_type, fingerprint, severity, confidence, summary, json.dumps(details)
    )

async def close_alert(conn, tenant_id, fingerprint):
    await conn.execute(
        """
        UPDATE fleet_alert
        SET status='CLOSED', closed_at=now()
        WHERE tenant_id=$1 AND fingerprint=$2 AND status='OPEN'
        """,
        tenant_id, fingerprint
    )

async def _influx_query(http_client: httpx.AsyncClient, db: str, sql: str) -> list[dict]:
    """Execute a SQL query against InfluxDB 3 Core and return list of row dicts."""
    try:
        resp = await http_client.post(
            f"{INFLUXDB_URL}/api/v3/query_sql",
            json={"db": db, "q": sql, "format": "json"},
            headers={
                "Authorization": f"Bearer {INFLUXDB_TOKEN}",
                "Content-Type": "application/json",
            },
        )
        if resp.status_code != 200:
            print(f"[evaluator] InfluxDB query error: {resp.status_code} {resp.text[:200]}")
            return []

        data = resp.json()

        # Handle different response formats from InfluxDB 3 Core
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            # Some versions return {"results": [...]} or {"data": [...]}
            if "results" in data:
                return data["results"]
            if "data" in data:
                return data["data"]
            if "columns" in data and "values" in data:
                columns = data.get("columns") or []
                values = data.get("values") or []
                rows = []
                for row in values:
                    if isinstance(row, list) and len(row) == len(columns):
                        rows.append({columns[i]: row[i] for i in range(len(columns))})
                return rows
        return []
    except Exception as e:
        print(f"[evaluator] InfluxDB query exception: {e}")
        return []


def _parse_influx_ts(val) -> datetime | None:
    """Parse a timestamp value from InfluxDB into a timezone-aware UTC datetime."""
    if val is None:
        return None
    if isinstance(val, datetime):
        return val
    if isinstance(val, (int, float)):
        # Nanosecond epoch
        return datetime.fromtimestamp(val / 1e9, tz=timezone.utc)
    if isinstance(val, str):
        try:
            dt = dtparser.isoparse(val)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except Exception:
            return None
    return None


async def fetch_rollup_influxdb(http_client: httpx.AsyncClient, pg_conn) -> list[dict]:
    """Fetch device rollup data from InfluxDB + PG device_registry.

    Returns list of dicts with keys:
    tenant_id, device_id, site_id, registry_status, last_hb, last_tel,
    last_seen, metrics (dict of all available metric fields)
    """
    # Step 1: Get all devices from PG registry
    devices = await pg_conn.fetch(
        "SELECT tenant_id, device_id, site_id, status FROM device_registry"
    )

    if not devices:
        return []

    # Group devices by tenant
    tenants: dict[str, list] = {}
    for d in devices:
        tid = d["tenant_id"]
        if tid not in tenants:
            tenants[tid] = []
        tenants[tid].append(d)

    results = []

    for tenant_id, tenant_devices in tenants.items():
        db_name = f"telemetry_{tenant_id}"

        # Step 2: Query heartbeat times
        hb_rows = await _influx_query(
            http_client, db_name,
            "SELECT device_id, MAX(time) AS last_hb FROM heartbeat "
            "WHERE time > now() - INTERVAL '30 minutes' GROUP BY device_id"
        )
        hb_map = {}
        for row in hb_rows:
            did = row.get("device_id")
            if did:
                hb_map[did] = _parse_influx_ts(row.get("last_hb"))

        # Step 3: Query telemetry times
        tel_rows = await _influx_query(
            http_client, db_name,
            "SELECT device_id, MAX(time) AS last_tel FROM telemetry "
            "WHERE time > now() - INTERVAL '30 minutes' GROUP BY device_id"
        )
        tel_map = {}
        for row in tel_rows:
            did = row.get("device_id")
            if did:
                tel_map[did] = _parse_influx_ts(row.get("last_tel"))

        # Step 4: Query latest metrics per device
        metrics_rows = await _influx_query(
            http_client, db_name,
            "SELECT * FROM telemetry WHERE time > now() - INTERVAL '30 minutes' "
            "ORDER BY time DESC"
        )
        # Deduplicate to latest per device_id
        metrics_map: dict[str, dict] = {}
        for row in metrics_rows:
            did = row.get("device_id")
            if did and did not in metrics_map:
                metrics_map[did] = row

        # Step 5: Merge into output format matching fetch_rollup()
        for d in tenant_devices:
            did = d["device_id"]
            last_hb = hb_map.get(did)
            last_tel = tel_map.get(did)

            # last_seen is the most recent of heartbeat or telemetry
            last_seen = None
            if last_hb and last_tel:
                last_seen = max(last_hb, last_tel)
            elif last_hb:
                last_seen = last_hb
            elif last_tel:
                last_seen = last_tel

            m = metrics_map.get(did, {})

            # Build metrics dict from all available fields, excluding metadata
            EXCLUDE_KEYS = {"time", "device_id", "site_id", "seq"}
            device_metrics = {}
            for key, value in m.items():
                if key in EXCLUDE_KEYS:
                    continue
                if str(key).startswith("iox::"):
                    continue
                if value is not None:
                    device_metrics[key] = value

            results.append({
                "tenant_id": d["tenant_id"],
                "device_id": did,
                "site_id": d["site_id"],
                "registry_status": d["status"],
                "last_hb": last_hb,
                "last_tel": last_tel,
                "last_seen": last_seen,
                "metrics": device_metrics,
            })

    return results

async def main():
    pool = await asyncpg.create_pool(
        host=PG_HOST, port=PG_PORT, database=PG_DB, user=PG_USER, password=PG_PASS,
        min_size=1, max_size=5
    )

    async with pool.acquire() as conn:
        await ensure_schema(conn)
    http_client = httpx.AsyncClient(timeout=10.0)

    while True:
        async with pool.acquire() as conn:
            rows = await fetch_rollup_influxdb(http_client, conn)

            for r in rows:
                tenant_id = r["tenant_id"]
                device_id = r["device_id"]
                site_id = r["site_id"]
                registry_status = r["registry_status"]
                last_hb = r["last_hb"]
                last_tel = r["last_tel"]
                last_seen = r["last_seen"]

                status = "STALE"
                if registry_status == "ACTIVE" and last_hb is not None:
                    age_s = (now_utc() - last_hb).total_seconds()
                    status = "ONLINE" if age_s <= HEARTBEAT_STALE_SECONDS else "STALE"

                state_blob = r.get("metrics", {})

                await conn.execute(
                    """
                    INSERT INTO device_state
                      (tenant_id, site_id, device_id, status, last_heartbeat_at, last_telemetry_at, last_seen_at, last_state_change_at, state)
                    VALUES
                      ($1,$2,$3,$4,$5,$6,$7, now(), $8::jsonb)
                    ON CONFLICT (tenant_id, device_id)
                    DO UPDATE SET
                      site_id = EXCLUDED.site_id,
                      last_heartbeat_at = EXCLUDED.last_heartbeat_at,
                      last_telemetry_at = EXCLUDED.last_telemetry_at,
                      last_seen_at = EXCLUDED.last_seen_at,
                      state = EXCLUDED.state,
                      status = EXCLUDED.status,
                      last_state_change_at = CASE
                        WHEN device_state.status IS DISTINCT FROM EXCLUDED.status THEN now()
                        ELSE device_state.last_state_change_at
                      END
                    """,
                    tenant_id, site_id, device_id, status, last_hb, last_tel, last_seen, json.dumps(state_blob)
                )

                fp_nohb = f"NO_HEARTBEAT:{device_id}"
                if status == "STALE":
                    await open_or_update_alert(
                        conn, tenant_id, site_id, device_id,
                        "NO_HEARTBEAT", fp_nohb,
                        4, 0.9,
                        f"{site_id}: {device_id} heartbeat missing/stale",
                        {"last_heartbeat_at": str(last_hb) if last_hb else None}
                    )
                else:
                    await close_alert(conn, tenant_id, fp_nohb)

        await asyncio.sleep(POLL_SECONDS)

if __name__ == "__main__":
    asyncio.run(main())
