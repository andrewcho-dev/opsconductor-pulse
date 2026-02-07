import asyncio
import json
import os
from aiohttp import web
from datetime import datetime, timezone
import asyncpg

PG_HOST = os.getenv("PG_HOST", "iot-postgres")
PG_PORT = int(os.getenv("PG_PORT", "5432"))
PG_DB   = os.getenv("PG_DB", "iotcloud")
PG_USER = os.getenv("PG_USER", "iot")
PG_PASS = os.getenv("PG_PASS", "iot_dev")

POLL_SECONDS = int(os.getenv("POLL_SECONDS", "5"))
HEARTBEAT_STALE_SECONDS = int(os.getenv("HEARTBEAT_STALE_SECONDS", "30"))
OPERATOR_SYMBOLS = {"GT": ">", "LT": "<", "GTE": ">=", "LTE": "<="}

COUNTERS = {
    "rules_evaluated": 0,
    "alerts_created": 0,
    "evaluation_errors": 0,
    "last_evaluation_at": None,
}

COUNTERS = {
    "rules_evaluated": 0,
    "alerts_created": 0,
    "evaluation_errors": 0,
    "last_evaluation_at": None,
}

async def health_handler(request):
    return web.json_response(
        {
            "status": "healthy",
            "service": "evaluator",
            "counters": {
                "rules_evaluated": COUNTERS["rules_evaluated"],
                "alerts_created": COUNTERS["alerts_created"],
                "evaluation_errors": COUNTERS["evaluation_errors"],
            },
            "last_evaluation_at": COUNTERS["last_evaluation_at"],
        }
    )


async def start_health_server():
    app = web.Application()
    app.router.add_get("/health", health_handler)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", 8080)
    await site.start()
    print("[health] evaluator health server started on port 8080")
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
# NOTE: alert_rules table is created by db/migrations/000_base_schema.sql
# and updated by db/migrations/025_fix_alert_rules_schema.sql

def now_utc():
    return datetime.now(timezone.utc)


async def health_handler(request):
    return web.json_response(
        {
            "status": "healthy",
            "service": "evaluator",
            "counters": {
                "rules_evaluated": COUNTERS["rules_evaluated"],
                "alerts_created": COUNTERS["alerts_created"],
                "evaluation_errors": COUNTERS["evaluation_errors"],
            },
            "last_evaluation_at": COUNTERS["last_evaluation_at"],
        }
    )


async def start_health_server():
    app = web.Application()
    app.router.add_get("/health", health_handler)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", 8080)
    await site.start()
    print("[health] evaluator health server started on port 8080")

async def ensure_schema(conn):
    for stmt in DDL.strip().split(";"):
        s = stmt.strip()
        if s:
            await conn.execute(s + ";")

async def open_or_update_alert(conn, tenant_id, site_id, device_id, alert_type, fingerprint, severity, confidence, summary, details):
    COUNTERS["alerts_created"] += 1
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

def evaluate_threshold(value, operator, threshold):
    """Check if a metric value triggers a threshold rule.

    Returns True if the condition is MET (alert should fire).
    """
    if value is None:
        return False
    try:
        value = float(value)
    except (TypeError, ValueError):
        return False
    if operator == "GT":
        return value > threshold
    elif operator == "LT":
        return value < threshold
    elif operator == "GTE":
        return value >= threshold
    elif operator == "LTE":
        return value <= threshold
    return False

async def fetch_tenant_rules(pg_conn, tenant_id):
    """Load enabled alert rules for a tenant from PostgreSQL."""
    rows = await pg_conn.fetch(
        """
        SELECT rule_id, name, metric_name, operator, threshold, severity, site_ids
        FROM alert_rules
        WHERE tenant_id = $1 AND enabled = true
        """,
        tenant_id
    )
    return [dict(r) for r in rows]

async def fetch_rollup_timescaledb(pg_conn) -> list[dict]:
    """Fetch device rollup data from TimescaleDB telemetry table + device_registry.

    Returns list of dicts with keys:
    tenant_id, device_id, site_id, registry_status, last_hb, last_tel,
    last_seen, metrics (dict of all available metric fields)
    """
    rows = await pg_conn.fetch(
        """
        WITH latest_telemetry AS (
            SELECT DISTINCT ON (tenant_id, device_id)
                tenant_id,
                device_id,
                time,
                msg_type,
                metrics
            FROM telemetry
            WHERE time > now() - INTERVAL '6 hours'
            ORDER BY tenant_id, device_id, time DESC
        ),
        latest_heartbeat AS (
            SELECT tenant_id, device_id, MAX(time) as last_hb
            FROM telemetry
            WHERE time > now() - INTERVAL '6 hours'
              AND msg_type = 'heartbeat'
            GROUP BY tenant_id, device_id
        ),
        latest_telemetry_time AS (
            SELECT tenant_id, device_id, MAX(time) as last_tel
            FROM telemetry
            WHERE time > now() - INTERVAL '6 hours'
              AND msg_type = 'telemetry'
            GROUP BY tenant_id, device_id
        )
        SELECT
            dr.tenant_id,
            dr.device_id,
            dr.site_id,
            dr.status as registry_status,
            lh.last_hb,
            lt.last_tel,
            GREATEST(lh.last_hb, lt.last_tel) as last_seen,
            COALESCE(ltel.metrics, '{}') as metrics
        FROM device_registry dr
        LEFT JOIN latest_heartbeat lh
            ON dr.tenant_id = lh.tenant_id AND dr.device_id = lh.device_id
        LEFT JOIN latest_telemetry_time lt
            ON dr.tenant_id = lt.tenant_id AND dr.device_id = lt.device_id
        LEFT JOIN latest_telemetry ltel
            ON dr.tenant_id = ltel.tenant_id AND dr.device_id = ltel.device_id
        """
    )

    results = []
    for r in rows:
        metrics_raw = r["metrics"]
        if isinstance(metrics_raw, str):
            try:
                metrics = json.loads(metrics_raw)
            except Exception:
                metrics = {}
        elif isinstance(metrics_raw, dict):
            metrics = metrics_raw
        else:
            metrics = {}

        results.append(
            {
                "tenant_id": r["tenant_id"],
                "device_id": r["device_id"],
                "site_id": r["site_id"],
                "registry_status": r["registry_status"],
                "last_hb": r["last_hb"],
                "last_tel": r["last_tel"],
                "last_seen": r["last_seen"],
                "metrics": metrics,
            }
        )

    return results

async def main():
    pool = await asyncpg.create_pool(
        host=PG_HOST, port=PG_PORT, database=PG_DB, user=PG_USER, password=PG_PASS,
        min_size=1, max_size=5
    )

    async with pool.acquire() as conn:
        await ensure_schema(conn)
    await start_health_server()

    while True:
        try:
            async with pool.acquire() as conn:
                rows = await fetch_rollup_timescaledb(conn)
                # Group devices by tenant for rule loading
                tenant_rules_cache = {}

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
                          state = CASE
                            WHEN EXCLUDED.state = '{}'::jsonb THEN device_state.state
                            ELSE EXCLUDED.state
                          END,
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

                    # --- Threshold rule evaluation ---
                    if tenant_id not in tenant_rules_cache:
                        tenant_rules_cache[tenant_id] = await fetch_tenant_rules(conn, tenant_id)

                    rules = tenant_rules_cache[tenant_id]
                    metrics = r.get("metrics", {})

                    for rule in rules:
                        COUNTERS["rules_evaluated"] += 1
                        rule_id = rule["rule_id"]
                        metric_name = rule["metric_name"]
                        operator = rule["operator"]
                        threshold = rule["threshold"]
                        rule_severity = rule["severity"]
                        rule_site_ids = rule.get("site_ids")

                        # Site filter: if rule has site_ids, skip devices not in those sites
                        if rule_site_ids and site_id not in rule_site_ids:
                            continue

                        fp_rule = f"RULE:{rule_id}:{device_id}"
                        metric_value = metrics.get(metric_name)

                        if metric_value is not None and evaluate_threshold(metric_value, operator, threshold):
                            # Condition MET — open/update alert
                            op_symbol = OPERATOR_SYMBOLS.get(operator, operator)
                            await open_or_update_alert(
                                conn, tenant_id, site_id, device_id,
                                "THRESHOLD", fp_rule,
                                rule_severity, 1.0,
                                f"{site_id}: {device_id} {metric_name} ({metric_value}) {op_symbol} {threshold}",
                                {
                                    "rule_id": rule_id,
                                    "rule_name": rule["name"],
                                    "metric_name": metric_name,
                                    "metric_value": metric_value,
                                    "operator": operator,
                                    "threshold": threshold,
                                }
                            )
                        else:
                            # Condition NOT met (or metric missing) — close alert if open
                            await close_alert(conn, tenant_id, fp_rule)

                total_rules = sum(len(v) for v in tenant_rules_cache.values())
                print(f"[evaluator] evaluated {len(rows)} devices, {total_rules} rules across {len(tenant_rules_cache)} tenants")
                COUNTERS["last_evaluation_at"] = now_utc().isoformat()
        except Exception as exc:
            COUNTERS["evaluation_errors"] += 1
            print(f"[evaluator] error={type(exc).__name__} {exc}")

        await asyncio.sleep(POLL_SECONDS)

if __name__ == "__main__":
    asyncio.run(main())
