import asyncio
import json
import os
from datetime import datetime, timezone
import asyncpg

PG_HOST = os.getenv("PG_HOST", "iot-postgres")
PG_PORT = int(os.getenv("PG_PORT", "5432"))
PG_DB   = os.getenv("PG_DB", "iotcloud")
PG_USER = os.getenv("PG_USER", "iot")
PG_PASS = os.getenv("PG_PASS", "iot_dev")

POLL_SECONDS = int(os.getenv("POLL_SECONDS", "5"))
HEARTBEAT_STALE_SECONDS = int(os.getenv("HEARTBEAT_STALE_SECONDS", "30"))

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

async def fetch_rollup(conn):
    rows = await conn.fetch(
        """
        WITH reg AS (
          SELECT tenant_id, device_id, site_id, status
          FROM device_registry
        ),
        times AS (
          SELECT
            tenant_id,
            device_id,
            MAX(CASE WHEN msg_type='heartbeat' THEN COALESCE(event_ts, ingested_at) END) AS last_hb,
            MAX(CASE WHEN msg_type='telemetry'  THEN COALESCE(event_ts, ingested_at) END) AS last_tel,
            MAX(COALESCE(event_ts, ingested_at)) AS last_seen
          FROM raw_events
          WHERE accepted=true
            AND ingested_at > (now() - interval '30 minutes')
          GROUP BY tenant_id, device_id
        ),
        latest_tel AS (
          SELECT DISTINCT ON (tenant_id, device_id)
            tenant_id,
            device_id,
            payload AS p
          FROM raw_events
          WHERE accepted=true
            AND msg_type='telemetry'
            AND ingested_at > (now() - interval '30 minutes')
          ORDER BY tenant_id, device_id, ingested_at DESC
        )
        SELECT
          r.tenant_id,
          r.device_id,
          r.site_id,
          r.status AS registry_status,
          t.last_hb,
          t.last_tel,
          t.last_seen,
          (lt.p->'metrics'->>'battery_pct')::float AS battery_pct,
          (lt.p->'metrics'->>'temp_c')::float AS temp_c,
          (lt.p->'metrics'->>'rssi_dbm')::int   AS rssi_dbm,
          (lt.p->'metrics'->>'snr_db')::float   AS snr_db,
          CASE
            WHEN (lt.p->'metrics'->>'uplink_ok') IS NULL THEN NULL
            WHEN (lt.p->'metrics'->>'uplink_ok') IN ('true','false') THEN (lt.p->'metrics'->>'uplink_ok')::boolean
            ELSE NULL
          END AS uplink_ok
        FROM reg r
        LEFT JOIN times t
          ON t.tenant_id=r.tenant_id AND t.device_id=r.device_id
        LEFT JOIN latest_tel lt
          ON lt.tenant_id=r.tenant_id AND lt.device_id=r.device_id
        ORDER BY r.tenant_id, r.site_id, r.device_id
        """
    )
    return rows

async def main():
    pool = await asyncpg.create_pool(
        host=PG_HOST, port=PG_PORT, database=PG_DB, user=PG_USER, password=PG_PASS,
        min_size=1, max_size=5
    )

    async with pool.acquire() as conn:
        await ensure_schema(conn)

    while True:
        async with pool.acquire() as conn:
            rows = await fetch_rollup(conn)

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

                state_blob = {
                    "battery_pct": r["battery_pct"],
                    "temp_c": r["temp_c"],
                    "rssi_dbm": r["rssi_dbm"],
                    "snr_db": r["snr_db"],
                    "uplink_ok": r["uplink_ok"],
                }
                state_blob = {k: v for k, v in state_blob.items() if v is not None}

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
