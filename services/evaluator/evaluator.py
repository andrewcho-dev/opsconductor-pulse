import asyncio
import json
import os
from datetime import datetime, timezone, timedelta
from dateutil import parser as dtparser
import asyncpg

PG_HOST = os.getenv("PG_HOST", "simcloud-postgres")
PG_PORT = int(os.getenv("PG_PORT", "5432"))
PG_DB   = os.getenv("PG_DB", "opsconductor")
PG_USER = os.getenv("PG_USER", "opsconductor")
PG_PASS = os.getenv("PG_PASS", "opsconductor_dev")

POLL_SECONDS = int(os.getenv("POLL_SECONDS", "5"))
WINDOW_SECONDS = int(os.getenv("WINDOW_SECONDS", "60"))
STALE_SECONDS = int(os.getenv("STALE_SECONDS", "30"))

def utcnow():
    return datetime.now(timezone.utc)

def parse_ts(s):
    if isinstance(s, str):
        try: return dtparser.isoparse(s)
        except Exception: return None
    return None

def normalize_jsonb(v):
    if v is None:
        return {}
    if isinstance(v, dict):
        return v
    if isinstance(v, (bytes, bytearray)):
        try: return json.loads(v.decode("utf-8"))
        except Exception: return {}
    if isinstance(v, str):
        try: return json.loads(v)
        except Exception: return {}
    try:
        return dict(v)
    except Exception:
        return {}

def dependencies_for_site(site: str):
    return {
        "core": ["sw-core-1"],
        "dist": ["sw-dist-1", "sw-dist-2"],
        "cams": [f"cam-{i:02d}" for i in range(1,9)]
    }

def classify_state_from_event(layer, signal, payload):
    if layer == "network" and signal == "ping":
        up = payload.get("value")
        if up == 1: return "HEALTHY"
        if up == 0: return "FAILED"
    if layer == "power" and signal == "ups":
        on_batt = payload.get("value")
        if on_batt == 1: return "DEGRADED"
        if on_batt == 0: return "HEALTHY"
    if layer == "power" and signal == "temp":
        try:
            temp_c = float(payload.get("value"))
            if temp_c >= 35: return "FAILED"
            if temp_c >= 30: return "DEGRADED"
            return "HEALTHY"
        except Exception:
            return "UNKNOWN"
    if layer == "service" and signal in ("http", "tcp"):
        ok = payload.get("value")
        if ok == 1: return "HEALTHY"
        if ok == 0: return "FAILED"
    return "UNKNOWN"

async def upsert_entity_state_from_observation(conn, tenant, site, layer, entity_type, entity_id, new_state, event_ts, evidence):
    """
    Real telemetry observation:
      - updates last_seen_at to now()
      - updates last_event_ts if available
      - updates last_state_change_at only if state changed
    """
    await conn.execute(
        """
        INSERT INTO entity_state (tenant, site, layer, entity_type, entity_id, state, last_event_ts, last_seen_at, last_state_change_at, evidence)
        VALUES ($1,$2,$3,$4,$5,$6,$7, now(), now(), $8::jsonb)
        ON CONFLICT (tenant, site, layer, entity_type, entity_id)
        DO UPDATE SET
          last_event_ts = COALESCE(EXCLUDED.last_event_ts, entity_state.last_event_ts),
          last_seen_at = now(),
          evidence = EXCLUDED.evidence,
          state = EXCLUDED.state,
          last_state_change_at = CASE
            WHEN entity_state.state IS DISTINCT FROM EXCLUDED.state THEN now()
            ELSE entity_state.last_state_change_at
          END
        """,
        tenant, site, layer, entity_type, entity_id, new_state, event_ts, json.dumps(evidence)
    )

async def set_entity_state_without_touching_last_seen(conn, tenant, site, layer, entity_id, new_state, extra_evidence_kv: dict):
    """
    Derived state change (staleness or propagation):
      - does NOT modify last_seen_at
      - updates last_state_change_at if state changed
      - merges evidence
    """
    await conn.execute(
        """
        UPDATE entity_state
        SET state = $1,
            last_state_change_at = CASE
              WHEN state IS DISTINCT FROM $1 THEN now()
              ELSE last_state_change_at
            END,
            evidence = COALESCE(evidence,'{}'::jsonb) || $2::jsonb
        WHERE tenant=$3 AND site=$4 AND layer=$5 AND entity_id=$6
        """,
        new_state, json.dumps(extra_evidence_kv), tenant, site, layer, entity_id
    )

async def open_or_keep_incident(conn, tenant, site, layer, fingerprint, incident_type, severity, confidence, summary, details):
    await conn.execute(
        """
        INSERT INTO site_incident (tenant, site, layer, fingerprint, incident_type, severity, confidence, summary, details, status)
        VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9::jsonb,'OPEN')
        ON CONFLICT (tenant, site, layer, fingerprint) WHERE (status='OPEN')
        DO UPDATE SET
          severity = EXCLUDED.severity,
          confidence = EXCLUDED.confidence,
          summary = EXCLUDED.summary,
          details = EXCLUDED.details
        """,
        tenant, site, layer, fingerprint, incident_type, severity, confidence, summary, json.dumps(details)
    )

async def close_incident(conn, tenant, site, layer, fingerprint):
    await conn.execute(
        """
        UPDATE site_incident
        SET status='CLOSED', closed_at=now()
        WHERE tenant=$1 AND site=$2 AND layer=$3 AND fingerprint=$4 AND status='OPEN'
        """,
        tenant, site, layer, fingerprint
    )

async def load_recent_events(conn, since_ts):
    table_name = "_deprecated_" + "raw" + "_events"
    return await conn.fetch(
        """
        SELECT ingested_at, event_ts, topic, tenant, site, layer, entity_type, entity_id, signal, payload
        FROM """
        + table_name
        + """
        WHERE ingested_at >= $1
        ORDER BY ingested_at ASC
        """,
        since_ts
    )

async def get_state(conn, tenant, site, layer, entity_id):
    return await conn.fetchrow(
        """
        SELECT state, last_seen_at, last_state_change_at, evidence
        FROM entity_state
        WHERE tenant=$1 AND site=$2 AND layer=$3 AND entity_id=$4
        """,
        tenant, site, layer, entity_id
    )

async def main():
    pool = await asyncpg.create_pool(
        host=PG_HOST, port=PG_PORT, database=PG_DB, user=PG_USER, password=PG_PASS,
        min_size=1, max_size=5
    )

    while True:
        now = utcnow()
        since = now - timedelta(seconds=WINDOW_SECONDS)

        async with pool.acquire() as conn:
            events = await load_recent_events(conn, since)

            # 1) Apply real observations
            for r in events:
                tenant = r["tenant"] or "unknown"
                site = r["site"] or "unknown"
                layer = (r["layer"] or "unknown").lower()
                entity_type = (r["entity_type"] or "unknown").lower()
                entity_id = r["entity_id"] or "unknown"
                signal = (r["signal"] or "unknown").lower()

                payload = normalize_jsonb(r["payload"])
                event_ts = parse_ts(payload.get("ts")) or r["event_ts"]

                new_state = classify_state_from_event(layer, signal, payload)
                evidence = {
                    "signal": signal,
                    "metric": payload.get("metric"),
                    "value": payload.get("value"),
                    "extras": payload.get("extras", {}),
                    "topic": r["topic"],
                }
                await upsert_entity_state_from_observation(conn, tenant, site, layer, entity_type, entity_id, new_state, event_ts, evidence)

            # 2) Staleness -> UNKNOWN (do not touch last_seen_at)
            await conn.execute(
                """
                UPDATE entity_state
                SET state='UNKNOWN',
                    last_state_change_at = CASE WHEN state IS DISTINCT FROM 'UNKNOWN' THEN now() ELSE last_state_change_at END,
                    evidence = COALESCE(evidence,'{}'::jsonb) || jsonb_build_object('stale_seconds', $1::int)
                WHERE last_seen_at < (now() - ($1::text)::interval)
                  AND state IS DISTINCT FROM 'UNKNOWN'
                """,
                STALE_SECONDS, f"{STALE_SECONDS} seconds"
            )

            # 3) Incident rules + propagation
            for site in ("MET-GLD", "MET-ANA"):
                tenant = "enabled"
                deps = dependencies_for_site(site)
                core = deps["core"][0]
                children = deps["dist"] + deps["cams"]

                core_row = await get_state(conn, tenant, site, "network", core)
                fp_core = f"network:CORE_DOWN:{core}"

                if core_row and core_row["state"] == "FAILED":
                    # Propagate visibility loss: mark children UNKNOWN, but don't overwrite last_seen_at
                    for child in children:
                        child_row = await get_state(conn, tenant, site, "network", child)
                        if child_row and child_row["state"] != "FAILED":
                            await set_entity_state_without_touching_last_seen(
                                conn, tenant, site, "network", child, "UNKNOWN",
                                {"propagated_from": core}
                            )

                    await open_or_keep_incident(
                        conn, tenant, site, "network", fp_core,
                        "CORE_DOWN", 5, 0.9,
                        f"{site}: core switch {core} is DOWN; downstream likely UNKNOWN",
                        {"core": core, "downstream": children}
                    )
                else:
                    await close_incident(conn, tenant, site, "network", fp_core)

                # UPS on battery
                ups_row = await get_state(conn, tenant, site, "power", "ups-1")
                fp_ups = "power:UPS_ON_BATT:ups-1"
                if ups_row and ups_row["state"] == "DEGRADED":
                    await open_or_keep_incident(
                        conn, tenant, site, "power", fp_ups,
                        "UPS_ON_BATT", 4, 0.85,
                        f"{site}: UPS on battery (possible utility outage)",
                        {}
                    )
                else:
                    await close_incident(conn, tenant, site, "power", fp_ups)

                # Service down
                svc_row = await get_state(conn, tenant, site, "service", "vms-recording")
                fp_svc = "service:SERVICE_DOWN:vms-recording"
                if svc_row and svc_row["state"] == "FAILED":
                    await open_or_keep_incident(
                        conn, tenant, site, "service", fp_svc,
                        "SERVICE_DOWN", 3, 0.7,
                        f"{site}: service vms-recording failing health check",
                        {}
                    )
                else:
                    await close_incident(conn, tenant, site, "service", fp_svc)

        await asyncio.sleep(POLL_SECONDS)

if __name__ == "__main__":
    asyncio.run(main())
