import asyncio
import json
import os
import logging
import time
import contextlib
import uuid
from collections import deque
from aiohttp import web
from datetime import datetime, timezone
import asyncpg
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
from shared.audit import init_audit_logger, get_audit_logger
from shared.logging import trace_id_var
from shared.logging import configure_logging, log_event
from shared.metrics import (
    evaluator_rules_evaluated_total,
    evaluator_alerts_created_total,
    evaluator_evaluation_errors_total,
    pulse_queue_depth,
    pulse_processing_duration_seconds,
    pulse_db_pool_size,
    pulse_db_pool_free,
)

# PHASE 44 AUDIT — Time-Window Rules
#
# fetch_tenant_rules() currently selects:
#   rule_id, name, metric_name, operator, threshold, severity, site_ids
#   MISSING: duration_seconds (to be added via migration + prompt 002)
#
# Evaluation flow (per device, per rule):
#   1. evaluate_threshold(value, operator, threshold) → True/False (immediate)
#   2. If True → open_or_update_alert()
#   3. If False → close_alert()
#   No time-window check exists yet.
#
# Phase 44 change: after evaluate_threshold() returns True,
# if rule["duration_seconds"] > 0, query telemetry to confirm
# the threshold has been continuously breached for duration_seconds.
# Only then fire the alert.

PG_HOST = os.getenv("PG_HOST", "iot-postgres")
PG_PORT = int(os.getenv("PG_PORT", "5432"))
PG_DB   = os.getenv("PG_DB", "iotcloud")
PG_USER = os.getenv("PG_USER", "iot")
PG_PASS = os.environ["PG_PASS"]
DATABASE_URL = os.getenv("DATABASE_URL")
configure_logging("evaluator")
logger = logging.getLogger("evaluator")

POLL_SECONDS = int(os.getenv("POLL_SECONDS", "5"))
HEARTBEAT_STALE_SECONDS = int(os.getenv("HEARTBEAT_STALE_SECONDS", "30"))
OPERATOR_SQL = {"GT": ">", "GTE": ">=", "LT": "<", "LTE": "<="}
OPERATOR_SYMBOLS = OPERATOR_SQL

COUNTERS = {
    "rules_evaluated": 0,
    "alerts_created": 0,
    "evaluation_errors": 0,
    "last_evaluation_at": None,
}

# In-memory sliding window buffer for WINDOW rules.
# Key: (device_id, rule_id) -> deque of (timestamp: float, value: float)
_window_buffers: dict[tuple[str, str], deque] = {}

# Shared state for LISTEN/NOTIFY wakeups.
_pending_tenants: set[str] = set()
_notify_event = asyncio.Event()
NOTIFY_CHANNEL = "telemetry_inserted"

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


async def metrics_handler(_request):
    return web.Response(body=generate_latest(), content_type=CONTENT_TYPE_LATEST.split(";")[0])


async def start_health_server():
    app = web.Application()
    app.router.add_get("/health", health_handler)
    app.router.add_get("/metrics", metrics_handler)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", 8080)
    await site.start()
    log_event(logger, "health server started", service_port=8080)
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

CREATE UNIQUE INDEX IF NOT EXISTS idx_fleet_alert_open_uq
ON fleet_alert (tenant_id, fingerprint)
WHERE status IN ('OPEN', 'ACKNOWLEDGED');

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
    app.router.add_get("/metrics", metrics_handler)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", 8080)
    await site.start()
    log_event(logger, "health server started", service_port=8080)

async def ensure_schema(conn):
    for stmt in DDL.strip().split(";"):
        s = stmt.strip()
        if s:
            await conn.execute(s + ";")

async def open_or_update_alert(conn, tenant_id, site_id, device_id, alert_type, fingerprint, severity, confidence, summary, details):
    COUNTERS["alerts_created"] += 1
    evaluator_alerts_created_total.labels(tenant_id=tenant_id).inc()
    row = await conn.fetchrow(
        """
        INSERT INTO fleet_alert (tenant_id, site_id, device_id, alert_type, fingerprint, status, severity, confidence, summary, details)
        VALUES ($1,$2,$3,$4,$5,'OPEN',$6,$7,$8,$9::jsonb)
        ON CONFLICT (tenant_id, fingerprint) WHERE (status IN ('OPEN', 'ACKNOWLEDGED'))
        DO UPDATE SET
          severity = EXCLUDED.severity,
          confidence = EXCLUDED.confidence,
          summary = EXCLUDED.summary,
          details = EXCLUDED.details
        RETURNING id, (xmax = 0) AS inserted
        """,
        tenant_id, site_id, device_id, alert_type, fingerprint, severity, confidence, summary, json.dumps(details)
    )
    if row:
        return row["id"], row["inserted"]
    return None, False

async def close_alert(conn, tenant_id, fingerprint):
    await conn.execute(
        """
        UPDATE fleet_alert
        SET status='CLOSED', closed_at=now()
        WHERE tenant_id=$1 AND fingerprint=$2 AND status IN ('OPEN', 'ACKNOWLEDGED')
        """,
        tenant_id, fingerprint
    )


async def deduplicate_or_create_alert(
    conn,
    tenant_id: str,
    site_id: str,
    device_id: str,
    alert_type: str,
    fingerprint: str,
    severity: int,
    confidence: float,
    summary: str,
    details: dict,
    rule_id: str | None = None,
) -> tuple[int | None, bool]:
    """
    Check for an existing open/acknowledged alert for the same device + rule.
    If found: increment trigger_count and update last_triggered_at, return (id, False).
    If not found: create a new alert, return (id, True).
    """
    if rule_id:
        existing = await conn.fetchrow(
            """
            SELECT id FROM fleet_alert
            WHERE device_id = $1
              AND rule_id = $2::uuid
              AND status IN ('OPEN', 'ACKNOWLEDGED')
            LIMIT 1
            """,
            device_id,
            rule_id,
        )
        if existing:
            await conn.execute(
                """
                UPDATE fleet_alert
                SET trigger_count = trigger_count + 1,
                    last_triggered_at = now(),
                    severity = $2,
                    summary = $3,
                    details = $4::jsonb
                WHERE id = $1
                """,
                existing["id"],
                severity,
                summary,
                json.dumps(details),
            )
            return existing["id"], False

    # No existing alert -- create new one
    COUNTERS["alerts_created"] += 1
    evaluator_alerts_created_total.labels(tenant_id=tenant_id).inc()
    row = await conn.fetchrow(
        """
        INSERT INTO fleet_alert
            (tenant_id, site_id, device_id, alert_type, fingerprint, status,
             severity, confidence, summary, details, rule_id, trigger_count, last_triggered_at)
        VALUES ($1, $2, $3, $4, $5, 'OPEN', $6, $7, $8, $9::jsonb, $10::uuid, 1, now())
        ON CONFLICT (tenant_id, fingerprint) WHERE (status IN ('OPEN', 'ACKNOWLEDGED'))
        DO UPDATE SET
          severity = EXCLUDED.severity,
          confidence = EXCLUDED.confidence,
          summary = EXCLUDED.summary,
          details = EXCLUDED.details,
          trigger_count = fleet_alert.trigger_count + 1,
          last_triggered_at = now()
        RETURNING id, (xmax = 0) AS inserted
        """,
        tenant_id,
        site_id,
        device_id,
        alert_type,
        fingerprint,
        severity,
        confidence,
        summary,
        json.dumps(details),
        rule_id,
    )
    if row:
        return row["id"], row["inserted"]
    return None, False


async def is_silenced(conn, tenant_id: str, fingerprint: str) -> bool:
    row = await conn.fetchrow(
        """
        SELECT silenced_until
        FROM fleet_alert
        WHERE tenant_id = $1
          AND fingerprint = $2
          AND status IN ('OPEN', 'ACKNOWLEDGED')
          AND silenced_until > now()
        LIMIT 1
        """,
        tenant_id,
        fingerprint,
    )
    return row is not None


async def is_in_maintenance(
    conn,
    tenant_id: str,
    site_id: str | None = None,
    device_type: str | None = None,
) -> bool:
    """
    Returns True if tenant has an active maintenance window matching site/type filters.
    """
    now = datetime.now(timezone.utc)
    rows = await conn.fetch(
        """
        SELECT window_id, recurring, site_ids, device_types, starts_at, ends_at
        FROM alert_maintenance_windows
        WHERE tenant_id = $1
          AND enabled = true
          AND starts_at <= $2
          AND (ends_at IS NULL OR ends_at > $2)
        """,
        tenant_id,
        now,
    )
    for row in rows:
        if row.get("site_ids") and site_id not in row["site_ids"]:
            continue
        if row.get("device_types") and device_type not in row["device_types"]:
            continue
        recurring = row.get("recurring")
        if recurring:
            schema_dow = (now.weekday() + 1) % 7  # 0=Sunday
            allowed_dows = recurring.get("dow", list(range(7)))
            if schema_dow not in allowed_dows:
                continue
            start_h = int(recurring.get("start_hour", 0))
            end_h = int(recurring.get("end_hour", 24))
            current_hour = now.hour
            if not (start_h <= current_hour < end_h):
                continue
        return True
    return False


async def check_telemetry_gap(
    conn,
    tenant_id: str,
    device_id: str,
    metric_name: str,
    gap_minutes: int,
) -> bool:
    """
    True when no telemetry metric data exists in the gap window.
    """
    row = await conn.fetchrow(
        """
        SELECT MAX(time) AS last_seen
        FROM telemetry
        WHERE tenant_id = $1
          AND device_id = $2
          AND metrics ? $3
          AND msg_type = 'telemetry'
          AND time > now() - ($4 || ' minutes')::interval
        """,
        tenant_id,
        device_id,
        metric_name,
        str(gap_minutes),
    )
    if row is None or row["last_seen"] is None:
        return True
    return False


async def maybe_process_telemetry_gap_rule(
    conn,
    tenant_id: str,
    site_id: str,
    device_id: str,
    rule: dict,
    rule_id,
    rule_severity: int,
    fingerprint: str,
) -> None:
    cfg = rule.get("conditions") or {}
    gap_metric = cfg.get("metric_name")
    if not gap_metric:
        return
    try:
        gap_minutes = int(cfg.get("gap_minutes", 10))
    except (TypeError, ValueError):
        return

    has_gap = await check_telemetry_gap(conn, tenant_id, device_id, gap_metric, gap_minutes)
    if has_gap:
        if await is_silenced(conn, tenant_id, fingerprint):
            return
        if await is_in_maintenance(
            conn,
            tenant_id,
            site_id=site_id,
            device_type=rule.get("device_type"),
        ):
            return
        summary = (
            f"{gap_metric} data gap on {device_id}: "
            f"no readings in last {gap_minutes} minutes"
        )
        await deduplicate_or_create_alert(
            conn,
            tenant_id,
            site_id,
            device_id,
            "NO_TELEMETRY",
            fingerprint,
            rule_severity,
            0.8,
            summary,
            {
                "rule_id": rule_id,
                "rule_name": rule["name"],
                "metric_name": gap_metric,
                "gap_minutes": gap_minutes,
            },
            rule_id=str(rule_id),
        )
    else:
        await close_alert(conn, tenant_id, fingerprint)


async def check_escalations(pool) -> int:
    """
    Escalate overdue OPEN alerts one time based on rule escalation_minutes.
    """
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            UPDATE fleet_alert fa
            SET
                severity = GREATEST(fa.severity - 1, 0),
                escalation_level = 1,
                escalated_at = now()
            FROM alert_rules ar
            WHERE fa.tenant_id = ar.tenant_id
              AND fa.status = 'OPEN'
              AND fa.escalation_level = 0
              AND (fa.silenced_until IS NULL OR fa.silenced_until <= now())
              AND ar.escalation_minutes IS NOT NULL
              AND (fa.details->>'rule_id') = ar.rule_id::text
              AND fa.created_at < now() - (ar.escalation_minutes || ' minutes')::interval
            RETURNING fa.id, fa.tenant_id, fa.severity, fa.escalated_at
            """,
            timeout=10,
        )
    return len(rows)

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
    elif operator in ("EQ", "=="):
        return value == threshold
    elif operator in ("NE", "!="):
        return value != threshold
    elif operator == ">":
        return value > threshold
    elif operator == "<":
        return value < threshold
    elif operator == ">=":
        return value >= threshold
    elif operator == "<=":
        return value <= threshold
    return False


AGGREGATION_FUNCTIONS = {
    "avg": lambda values: sum(values) / len(values) if values else None,
    "min": lambda values: min(values) if values else None,
    "max": lambda values: max(values) if values else None,
    "count": lambda values: len(values),
    "sum": lambda values: sum(values) if values else None,
}


def update_window_buffer(
    device_id: str,
    rule_id: str,
    timestamp: float,
    value: float,
    window_seconds: int,
) -> None:
    """Append a data point and evict stale entries."""
    key = (device_id, rule_id)
    buf = _window_buffers.setdefault(key, deque())
    buf.append((timestamp, value))
    cutoff = timestamp - window_seconds
    while buf and buf[0][0] < cutoff:
        buf.popleft()


def evaluate_window_aggregation(
    device_id: str,
    rule_id: str,
    aggregation: str,
    operator: str,
    threshold: float,
    window_seconds: int,
) -> bool:
    """
    Apply aggregation to the buffered values and compare to threshold.
    Returns True if condition is met (alert should fire).
    Returns False if insufficient data or condition not met.
    """
    key = (device_id, rule_id)
    buf = _window_buffers.get(key)
    if not buf or len(buf) < 2:
        return False  # need at least 2 data points for meaningful aggregation

    values = [v for _, v in buf]
    agg_fn = AGGREGATION_FUNCTIONS.get(aggregation)
    if agg_fn is None:
        return False

    aggregated_value = agg_fn(values)
    if aggregated_value is None:
        return False

    return evaluate_threshold(aggregated_value, operator, threshold)


def compute_z_score(value: float, mean: float, stddev: float) -> float | None:
    """Returns Z-score or None if stddev is 0 (no variation)."""
    if stddev == 0:
        return None
    return abs(value - mean) / stddev


async def compute_rolling_stats(
    conn,
    tenant_id: str,
    device_id: str,
    metric_name: str,
    window_minutes: int,
) -> dict | None:
    """
    Compute rolling mean and stddev for a metric over the last window_minutes.
    Returns {"mean": float, "stddev": float, "count": int, "latest": float} or None.
    """
    row = await conn.fetchrow(
        """
        SELECT
            AVG((metrics->>$3)::numeric)    AS mean_val,
            STDDEV((metrics->>$3)::numeric) AS stddev_val,
            COUNT(*)                        AS sample_count,
            (
                SELECT (metrics->>$3)::numeric
                FROM telemetry
                WHERE tenant_id = $1
                  AND device_id = $2
                  AND metrics ? $3
                ORDER BY time DESC
                LIMIT 1
            )                               AS latest_val
        FROM telemetry
        WHERE tenant_id = $1
          AND device_id = $2
          AND time > now() - ($4 || ' minutes')::interval
          AND metrics ? $3
        """,
        tenant_id,
        device_id,
        metric_name,
        str(window_minutes),
    )
    if not row or row["sample_count"] is None or row["sample_count"] < 2:
        return None
    return {
        "mean": float(row["mean_val"]),
        "stddev": float(row["stddev_val"]) if row["stddev_val"] is not None else 0.0,
        "count": int(row["sample_count"]),
        "latest": float(row["latest_val"]) if row["latest_val"] is not None else None,
    }


def normalize_value(raw_value, multiplier, offset_value):
    if raw_value is None:
        return None
    try:
        numeric_value = float(raw_value)
    except (TypeError, ValueError):
        return None
    try:
        mult = float(multiplier)
    except (TypeError, ValueError):
        mult = 1.0
    try:
        offset = float(offset_value)
    except (TypeError, ValueError):
        offset = 0.0
    return (numeric_value * mult) + offset


def should_fire_heartbeat_alert(last_seen: datetime, timeout_seconds: int) -> bool:
    if last_seen is None:
        return True
    return (now_utc() - last_seen).total_seconds() > max(0, int(timeout_seconds))

async def fetch_tenant_rules(pg_conn, tenant_id):
    """Load enabled alert rules for a tenant from PostgreSQL."""
    rows = await pg_conn.fetch(
        """
        SELECT rule_id, name, rule_type, metric_name, operator, threshold, severity,
               site_ids, group_ids, conditions, match_mode, duration_seconds, duration_minutes,
               aggregation, window_seconds
        FROM alert_rules
        WHERE tenant_id = $1 AND enabled = true
        """,
        tenant_id
    )
    return [dict(r) for r in rows]


def _evaluate_single_condition(
    metric_value: float | None,
    operator: str,
    threshold: float,
) -> bool:
    """Evaluate one condition against a scalar metric value."""
    if metric_value is None:
        return False
    op = OPERATOR_SQL.get(operator)
    if op is None:
        return False
    if op == ">":
        return metric_value > threshold
    if op == ">=":
        return metric_value >= threshold
    if op == "<":
        return metric_value < threshold
    if op == "<=":
        return metric_value <= threshold
    return False


async def _evaluate_condition_with_window(
    conn,
    tenant_id: str,
    device_id: str,
    condition: dict,
    rule_duration_minutes: int | None,
    latest_metrics_snapshot: dict,
    mappings_by_normalized: dict[str, list[dict]],
) -> bool:
    """
    Evaluate a single condition.
    Per-condition duration takes precedence over the rule-level duration.
    """
    metric_name = condition.get("metric_name")
    operator = condition.get("operator")
    threshold = condition.get("threshold")
    if metric_name is None or operator is None or threshold is None:
        return False
    try:
        threshold_value = float(threshold)
    except (TypeError, ValueError):
        return False

    duration = condition.get("duration_minutes")
    if duration is None:
        duration = rule_duration_minutes
    if duration:
        try:
            duration_value = int(duration)
        except (TypeError, ValueError):
            return False
        if duration_value <= 0:
            return False
        mappings = mappings_by_normalized.get(metric_name, [])
        return await _condition_holds_for_window(
            conn,
            tenant_id,
            device_id,
            metric_name,
            operator,
            threshold_value,
            duration_value,
            mappings=mappings if mappings else None,
        )

    latest_value = latest_metrics_snapshot.get(metric_name)
    try:
        numeric_value = float(latest_value) if latest_value is not None else None
    except (TypeError, ValueError):
        numeric_value = None
    return _evaluate_single_condition(numeric_value, operator, threshold_value)


async def _evaluate_rule_conditions(
    conn,
    tenant_id: str,
    device_id: str,
    rule: dict,
    latest_metrics_snapshot: dict,
    mappings_by_normalized: dict[str, list[dict]],
) -> bool:
    """
    Evaluate all conditions for a rule applying match_mode (all/any).
    Falls back to legacy metric_name/operator/threshold when conditions is empty.
    """
    conditions = rule.get("conditions")
    match_mode = str(rule.get("match_mode") or "all").lower()

    if isinstance(conditions, dict):
        # Backwards compatibility for old JSON shape:
        # {"combinator":"AND|OR","conditions":[...]}
        combinator = str(conditions.get("combinator", "AND")).upper()
        legacy_conditions = conditions.get("conditions")
        if isinstance(legacy_conditions, list):
            conditions = legacy_conditions
            if match_mode not in {"all", "any"}:
                match_mode = "any" if combinator == "OR" else "all"

    if not isinstance(conditions, list) or not conditions:
        metric_name = rule.get("metric_name")
        operator = rule.get("operator")
        threshold = rule.get("threshold")
        if metric_name is None or operator is None or threshold is None:
            return False
        latest_value = latest_metrics_snapshot.get(metric_name)
        try:
            numeric_value = float(latest_value) if latest_value is not None else None
            threshold_value = float(threshold)
        except (TypeError, ValueError):
            return False
        duration_minutes = rule.get("duration_minutes")
        if duration_minutes:
            try:
                duration_value = int(duration_minutes)
            except (TypeError, ValueError):
                return False
            mappings = mappings_by_normalized.get(metric_name, [])
            return await _condition_holds_for_window(
                conn,
                tenant_id,
                device_id,
                metric_name,
                operator,
                threshold_value,
                duration_value,
                mappings=mappings if mappings else None,
            )
        return _evaluate_single_condition(numeric_value, operator, threshold_value)

    if match_mode not in {"all", "any"}:
        match_mode = "all"

    results: list[bool] = []
    for condition in conditions:
        result = await _evaluate_condition_with_window(
            conn=conn,
            tenant_id=tenant_id,
            device_id=device_id,
            condition=condition,
            rule_duration_minutes=rule.get("duration_minutes"),
            latest_metrics_snapshot=latest_metrics_snapshot,
            mappings_by_normalized=mappings_by_normalized,
        )
        results.append(result)
        if match_mode == "any" and result:
            return True
        if match_mode == "all" and not result:
            return False
    return all(results) if match_mode == "all" else any(results)


def evaluate_conditions(metrics_snapshot: dict, conditions_json) -> bool:
    """Compatibility helper used by existing unit tests."""
    conditions = conditions_json
    match_mode = "all"
    if isinstance(conditions_json, dict):
        if isinstance(conditions_json.get("conditions"), list):
            conditions = conditions_json.get("conditions")
            combinator = str(conditions_json.get("combinator", "AND")).upper()
            match_mode = "any" if combinator == "OR" else "all"
    if not isinstance(conditions, list) or not conditions:
        return False

    results: list[bool] = []
    for condition in conditions:
        metric_name = condition.get("metric_name")
        operator = condition.get("operator")
        threshold = condition.get("threshold")
        if metric_name is None or operator is None or threshold is None:
            results.append(False)
            continue
        metric_value = metrics_snapshot.get(metric_name)
        try:
            numeric_value = float(metric_value) if metric_value is not None else None
            threshold_value = float(threshold)
        except (TypeError, ValueError):
            results.append(False)
            continue
        result = _evaluate_single_condition(numeric_value, operator, threshold_value)
        results.append(result)
        if match_mode == "any" and result:
            return True
        if match_mode == "all" and not result:
            return False
    return all(results) if match_mode == "all" else any(results)


async def check_duration_window(
    conn,
    tenant_id: str,
    device_id: str,
    metric_name: str,
    operator: str,
    threshold: float,
    duration_seconds: int,
    mappings: list[dict] | None = None,
) -> bool:
    """
    Returns True if the threshold condition has been continuously met
    for at least duration_seconds.

    Uses the telemetry hypertable: counts readings in the window that
    do NOT breach the threshold. If that count is 0 AND the window
    contains at least one reading older than (now - duration_seconds + POLL_SECONDS),
    the condition has been continuously true.

    mappings: list of {raw_metric, multiplier, offset_value} dicts if metric
    is normalized. If None or empty, uses metric_name directly as raw column.
    """
    if duration_seconds <= 0:
        return True  # No window required — fire immediately

    op_sql = OPERATOR_SQL.get(operator)
    if not op_sql:
        return False

    if mappings:
        m = mappings[0]
        raw_metric = m["raw_metric"]
        mult = float(m.get("multiplier") or 1.0)
        offset = float(m.get("offset_value") or 0.0)

        failing_count = await conn.fetchval(
            f"""
            SELECT COUNT(*)
            FROM telemetry
            WHERE tenant_id = $1
              AND device_id = $2
              AND metrics ? $3
              AND time >= now() - make_interval(secs => $4::int)
              AND (
                (metrics->>$3)::numeric * $5 + $6
              ) {op_sql} $7 IS NOT TRUE
            """,
            tenant_id, device_id, raw_metric, duration_seconds, mult, offset, threshold
        )

        total_count = await conn.fetchval(
            """
            SELECT COUNT(*)
            FROM telemetry
            WHERE tenant_id = $1
              AND device_id = $2
              AND metrics ? $3
              AND time >= now() - make_interval(secs => $4::int)
            """,
            tenant_id, device_id, raw_metric, duration_seconds
        )
    else:
        failing_count = await conn.fetchval(
            f"""
            SELECT COUNT(*)
            FROM telemetry
            WHERE tenant_id = $1
              AND device_id = $2
              AND metrics ? $3
              AND time >= now() - make_interval(secs => $4::int)
              AND (metrics->>$3)::numeric {op_sql} $5 IS NOT TRUE
            """,
            tenant_id, device_id, metric_name, duration_seconds, threshold
        )

        total_count = await conn.fetchval(
            """
            SELECT COUNT(*)
            FROM telemetry
            WHERE tenant_id = $1
              AND device_id = $2
              AND metrics ? $3
              AND time >= now() - make_interval(secs => $4::int)
            """,
            tenant_id, device_id, metric_name, duration_seconds
        )

    return (
        total_count is not None
        and total_count > 0
        and failing_count is not None
        and failing_count == 0
    )


async def _condition_holds_for_window(
    conn,
    tenant_id: str,
    device_id: str,
    metric_name: str,
    operator: str,
    threshold: float,
    duration_minutes: int,
    mappings: list[dict] | None = None,
) -> bool:
    """
    Compatibility wrapper for minute-based rule windows.
    """
    return await check_duration_window(
        conn=conn,
        tenant_id=tenant_id,
        device_id=device_id,
        metric_name=metric_name,
        operator=operator,
        threshold=threshold,
        duration_seconds=int(duration_minutes) * 60,
        mappings=mappings,
    )


async def fetch_metric_mappings(pg_conn, tenant_id):
    rows = await pg_conn.fetch(
        """
        SELECT raw_metric, normalized_name, multiplier, offset_value
        FROM metric_mappings
        WHERE tenant_id = $1
        """,
        tenant_id,
    )
    mapping_by_normalized: dict[str, list[dict]] = {}
    for row in rows:
        mapping_by_normalized.setdefault(row["normalized_name"], []).append(
            {
                "raw_metric": row["raw_metric"],
                "multiplier": row["multiplier"],
                "offset_value": row["offset_value"],
            }
        )
    return mapping_by_normalized

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


async def create_listener_conn(host, port, database, user, password):
    """Create a dedicated asyncpg connection for LISTEN (not from pool)."""
    return await asyncpg.connect(
        host=host, port=port, database=database, user=user, password=password
    )


def resolve_notify_dsn() -> str:
    return os.environ.get("NOTIFY_DATABASE_URL", os.environ.get("DATABASE_URL", ""))


async def init_notify_listener(channel: str, callback):
    notify_dsn = resolve_notify_dsn()
    if notify_dsn:
        conn = await asyncpg.connect(notify_dsn)
    else:
        conn = await create_listener_conn(PG_HOST, PG_PORT, PG_DB, PG_USER, PG_PASS)
    await conn.add_listener(channel, callback)
    return conn


async def close_notify_listener(conn, channel: str, callback) -> None:
    if conn is None:
        return
    try:
        await conn.remove_listener(channel, callback)
    except Exception:
        pass
    await conn.close()


def on_telemetry_notify(conn, pid, channel, payload):
    """Called by asyncpg when a telemetry notification arrives."""
    payload = (payload or "").strip()
    if payload:
        try:
            parsed = json.loads(payload)
            if isinstance(parsed, dict):
                tenant_ids = parsed.get("tenant_ids") or []
                for tenant_id in tenant_ids:
                    if tenant_id:
                        _pending_tenants.add(str(tenant_id))
            elif isinstance(parsed, str) and parsed:
                _pending_tenants.add(parsed)
        except Exception:
            _pending_tenants.add(payload)
    _notify_event.set()


async def maintain_notify_listener(channel: str, callback, stop_event: asyncio.Event) -> None:
    while not stop_event.is_set():
        listener_conn = None
        try:
            listener_conn = await init_notify_listener(channel, callback)
            log_event(logger, "listen channel active", channel=channel)
            while not stop_event.is_set():
                if listener_conn.is_closed():
                    log_event(
                        logger,
                        "listener connection dropped, reconnecting",
                        level="WARNING",
                        channel=channel,
                    )
                    break
                await asyncio.sleep(1)
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            log_event(
                logger,
                "listener setup failed, retrying",
                level="WARNING",
                channel=channel,
                error=str(exc),
            )
            await asyncio.sleep(2)
        finally:
            await close_notify_listener(listener_conn, channel, callback)
        if not stop_event.is_set():
            await asyncio.sleep(2)

async def main():
    if DATABASE_URL:
        pool = await asyncpg.create_pool(dsn=DATABASE_URL, min_size=2, max_size=10, command_timeout=30)
    else:
        pool = await asyncpg.create_pool(
            host=PG_HOST, port=PG_PORT, database=PG_DB, user=PG_USER, password=PG_PASS,
            min_size=2, max_size=10, command_timeout=30
        )

    async with pool.acquire() as conn:
        await ensure_schema(conn)
    await start_health_server()
    audit = init_audit_logger(pool, "evaluator")
    await audit.start()

    fallback_poll_seconds = int(os.getenv("FALLBACK_POLL_SECONDS", str(POLL_SECONDS)))
    debounce_seconds = float(os.getenv("DEBOUNCE_SECONDS", "0.5"))

    stop_listener = asyncio.Event()
    listener_task = asyncio.create_task(
        maintain_notify_listener(NOTIFY_CHANNEL, on_telemetry_notify, stop_listener)
    )

    try:
        last_escalation_check = 0.0
        while True:
            trace_token = trace_id_var.set(str(uuid.uuid4()))
            conn = None
            try:
                log_event(logger, "tick_start", tick="evaluator")
                eval_start = time.monotonic()
                try:
                    await asyncio.wait_for(_notify_event.wait(), timeout=fallback_poll_seconds)
                except asyncio.TimeoutError:
                    log_event(
                        logger,
                        "fallback poll triggered",
                        level="WARNING",
                        reason="no notifications",
                    )

                _notify_event.clear()
                await asyncio.sleep(debounce_seconds)
                _notify_event.clear()
                _pending_tenants.clear()

                conn = await pool.acquire()
                rows = await fetch_rollup_timescaledb(conn)
                pulse_queue_depth.labels(
                    service="evaluator",
                    queue_name="devices_to_evaluate",
                ).set(len(rows))
                # Group devices by tenant for rule loading
                tenant_rules_cache = {}
                tenant_mapping_cache = {}

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

                    now_ts = now_utc()
                    row = await conn.fetchrow(
                        """
                        WITH existing AS (
                            SELECT status
                            FROM device_state
                            WHERE tenant_id = $1 AND device_id = $3
                        )
                        INSERT INTO device_state
                          (tenant_id, site_id, device_id, status, last_heartbeat_at, last_telemetry_at, last_seen_at, last_state_change_at, state)
                        VALUES
                          ($1,$2,$3,$4,$5,$6,$7,$8, $9::jsonb)
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
                            WHEN device_state.status IS DISTINCT FROM EXCLUDED.status THEN $8
                            ELSE device_state.last_state_change_at
                          END
                        RETURNING
                          (SELECT status FROM existing) AS previous_status,
                          status AS new_status,
                          last_state_change_at
                        """,
                        tenant_id,
                        site_id,
                        device_id,
                        status,
                        last_hb,
                        last_tel,
                        last_seen,
                        now_ts,
                        json.dumps(state_blob),
                    )
                    if row:
                        previous_status = row["previous_status"]
                        new_status = row["new_status"]
                        if previous_status and previous_status != new_status:
                            audit = get_audit_logger()
                            if audit:
                                audit.device_state_change(
                                    tenant_id,
                                    device_id,
                                    str(previous_status).lower(),
                                    str(new_status).lower(),
                                )

                    fp_nohb = f"NO_HEARTBEAT:{device_id}"
                    if status == "STALE":
                        if not await is_in_maintenance(
                            conn, tenant_id, site_id=site_id, device_type=None
                        ):
                            alert_id, inserted = await open_or_update_alert(
                                conn, tenant_id, site_id, device_id,
                                "NO_HEARTBEAT", fp_nohb,
                                4, 0.9,
                                f"{site_id}: {device_id} heartbeat missing/stale",
                                {"last_heartbeat_at": str(last_hb) if last_hb else None}
                            )
                            if inserted:
                                audit = get_audit_logger()
                                if audit:
                                    audit.alert_created(
                                        tenant_id,
                                        str(alert_id),
                                        "NO_HEARTBEAT",
                                        device_id,
                                        f"{site_id}: {device_id} heartbeat missing/stale",
                                    )
                    else:
                        await close_alert(conn, tenant_id, fp_nohb)

                    # --- Threshold rule evaluation ---
                    if tenant_id not in tenant_rules_cache:
                        tenant_rules_cache[tenant_id] = await fetch_tenant_rules(conn, tenant_id)
                    if tenant_id not in tenant_mapping_cache:
                        tenant_mapping_cache[tenant_id] = await fetch_metric_mappings(conn, tenant_id)

                    rules = tenant_rules_cache[tenant_id]
                    metrics = r.get("metrics", {})
                    mappings_by_normalized = tenant_mapping_cache[tenant_id]
                    latest_metrics_snapshot = dict(metrics)
                    for normalized_name, mappings in mappings_by_normalized.items():
                        for mapping in mappings:
                            raw_value = metrics.get(mapping["raw_metric"])
                            normalized_value = normalize_value(
                                raw_value,
                                mapping["multiplier"],
                                mapping["offset_value"],
                            )
                            if normalized_value is not None:
                                latest_metrics_snapshot[normalized_name] = normalized_value
                                break

                    for rule in rules:
                        COUNTERS["rules_evaluated"] += 1
                        evaluator_rules_evaluated_total.labels(tenant_id=tenant_id).inc()
                        rule_id = rule["rule_id"]
                        rule_type = str(rule.get("rule_type") or "threshold").lower()
                        metric_name = rule["metric_name"]
                        operator = rule["operator"]
                        threshold = rule["threshold"]
                        rule_severity = rule["severity"]
                        rule_site_ids = rule.get("site_ids")

                        # Site filter: if rule has site_ids, skip devices not in those sites
                        if rule_site_ids and site_id not in rule_site_ids:
                            continue

                        if rule.get("group_ids"):
                            is_member = await conn.fetchval(
                                """
                                SELECT 1
                                FROM device_group_members
                                WHERE tenant_id = $1
                                  AND device_id = $2
                                  AND group_id = ANY($3::text[])
                                LIMIT 1
                                """,
                                tenant_id,
                                device_id,
                                rule["group_ids"],
                            )
                            if not is_member:
                                continue

                        fp_rule = f"RULE:{rule_id}:{device_id}"
                        conditions_json = rule.get("conditions")
                        if isinstance(conditions_json, str):
                            try:
                                conditions_json = json.loads(conditions_json)
                            except Exception:
                                conditions_json = {}

                        if rule_type == "telemetry_gap":
                            await maybe_process_telemetry_gap_rule(
                                conn=conn,
                                tenant_id=tenant_id,
                                site_id=site_id,
                                device_id=device_id,
                                rule=rule,
                                rule_id=rule_id,
                                rule_severity=rule_severity,
                                fingerprint=fp_rule,
                            )
                            continue

                        if rule_type == "window":
                            aggregation = rule.get("aggregation")
                            window_seconds = rule.get("window_seconds")
                            if not aggregation or not window_seconds:
                                continue

                            # Get the raw metric value from the latest snapshot
                            raw_value = latest_metrics_snapshot.get(metric_name)
                            if raw_value is not None:
                                try:
                                    numeric_value = float(raw_value)
                                except (TypeError, ValueError):
                                    continue
                                now_ts_float = time.time()
                                update_window_buffer(
                                    device_id,
                                    str(rule_id),
                                    now_ts_float,
                                    numeric_value,
                                    window_seconds,
                                )

                            fired = evaluate_window_aggregation(
                                device_id,
                                str(rule_id),
                                aggregation,
                                operator,
                                float(threshold),
                                window_seconds,
                            )
                            if not fired:
                                await close_alert(conn, tenant_id, fp_rule)
                                continue

                            if await is_silenced(conn, tenant_id, fp_rule):
                                continue
                            if await is_in_maintenance(
                                conn,
                                tenant_id,
                                site_id=site_id,
                                device_type=rule.get("device_type"),
                            ):
                                continue

                            # Format human-readable summary
                            window_display = (
                                f"{window_seconds // 60}m"
                                if window_seconds >= 60
                                else f"{window_seconds}s"
                            )
                            op_symbol = OPERATOR_SYMBOLS.get(operator, operator)
                            summary = (
                                f"{site_id}: {device_id} rule '{rule['name']}' triggered -- "
                                f"{aggregation}({metric_name}) {op_symbol} {threshold} over {window_display}"
                            )
                            alert_id, inserted = await deduplicate_or_create_alert(
                                conn,
                                tenant_id,
                                site_id,
                                device_id,
                                "WINDOW",
                                fp_rule,
                                rule_severity,
                                1.0,
                                summary,
                                {
                                    "rule_id": rule_id,
                                    "rule_name": rule["name"],
                                    "metric_name": metric_name,
                                    "aggregation": aggregation,
                                    "window_seconds": window_seconds,
                                    "operator": operator,
                                    "threshold": threshold,
                                },
                                rule_id=str(rule_id),
                            )
                            if inserted:
                                log_event(
                                    logger,
                                    "alert created",
                                    tenant_id=tenant_id,
                                    device_id=device_id,
                                    alert_type="WINDOW",
                                    alert_id=str(alert_id),
                                )
                            continue

                        if rule_type == "anomaly":
                            cfg = conditions_json or {}
                            anomaly_metric = cfg.get("metric_name")
                            if not anomaly_metric:
                                continue
                            try:
                                window_minutes = int(cfg.get("window_minutes", 60))
                                z_threshold = float(cfg.get("z_threshold", 3.0))
                                min_samples = int(cfg.get("min_samples", 10))
                            except (TypeError, ValueError):
                                continue

                            stats = await compute_rolling_stats(
                                conn, tenant_id, device_id, anomaly_metric, window_minutes
                            )
                            if stats is None or stats["count"] < min_samples or stats["latest"] is None:
                                continue

                            z_score = compute_z_score(stats["latest"], stats["mean"], stats["stddev"])
                            if z_score is None or z_score <= z_threshold:
                                await close_alert(conn, tenant_id, fp_rule)
                                continue

                            if await is_silenced(conn, tenant_id, fp_rule):
                                continue
                            if await is_in_maintenance(
                                conn,
                                tenant_id,
                                site_id=site_id,
                                device_type=rule.get("device_type"),
                            ):
                                continue
                            summary = (
                                f"{anomaly_metric} anomaly on {device_id}: "
                                f"value={stats['latest']:.2f}, mean={stats['mean']:.2f}, "
                                f"stddev={stats['stddev']:.2f}, z={z_score:.2f}"
                            )
                            await deduplicate_or_create_alert(
                                conn,
                                tenant_id,
                                site_id,
                                device_id,
                                "ANOMALY",
                                fp_rule,
                                rule_severity,
                                1.0,
                                summary,
                                {
                                    "rule_id": rule_id,
                                    "rule_name": rule["name"],
                                    "metric_name": anomaly_metric,
                                    "z_score": z_score,
                                    "z_threshold": z_threshold,
                                    **stats,
                                },
                                rule_id=str(rule_id),
                            )
                            continue

                        rule_for_eval = dict(rule)
                        rule_for_eval["conditions"] = conditions_json
                        fired = await _evaluate_rule_conditions(
                            conn=conn,
                            tenant_id=tenant_id,
                            device_id=device_id,
                            rule=rule_for_eval,
                            latest_metrics_snapshot=latest_metrics_snapshot,
                            mappings_by_normalized=mappings_by_normalized,
                        )
                        if not fired:
                            await close_alert(conn, tenant_id, fp_rule)
                            continue

                        if await is_silenced(conn, tenant_id, fp_rule):
                            continue
                        if await is_in_maintenance(
                            conn,
                            tenant_id,
                            site_id=site_id,
                            device_type=rule.get("device_type"),
                        ):
                            continue

                        active_conditions = conditions_json if isinstance(conditions_json, list) else []
                        if not active_conditions and metric_name and operator and threshold is not None:
                            active_conditions = [
                                {
                                    "metric_name": metric_name,
                                    "operator": operator,
                                    "threshold": threshold,
                                    "duration_minutes": rule.get("duration_minutes"),
                                }
                            ]
                        first_condition = active_conditions[0] if active_conditions else {}
                        detail_metric = first_condition.get("metric_name", metric_name)
                        detail_operator = first_condition.get("operator", operator)
                        detail_threshold = first_condition.get("threshold", threshold)
                        detail_value = latest_metrics_snapshot.get(detail_metric) if detail_metric else None
                        detail_match_mode = str(rule.get("match_mode") or "all")

                        summary = (
                            f"{site_id}: {device_id} rule '{rule['name']}' triggered "
                            f"({detail_match_mode})"
                        )
                        alert_id, inserted = await deduplicate_or_create_alert(
                            conn,
                            tenant_id,
                            site_id,
                            device_id,
                            "THRESHOLD",
                            fp_rule,
                            rule_severity,
                            1.0,
                            summary,
                            {
                                "rule_id": rule_id,
                                "rule_name": rule["name"],
                                "metric_name": detail_metric,
                                "metric_value": detail_value,
                                "operator": detail_operator,
                                "threshold": detail_threshold,
                                "match_mode": detail_match_mode,
                                "conditions": active_conditions,
                            },
                            rule_id=str(rule_id),
                        )
                        audit = get_audit_logger()
                        if audit and detail_metric and detail_operator and detail_threshold is not None:
                            try:
                                metric_value_numeric = float(detail_value) if detail_value is not None else 0.0
                            except (TypeError, ValueError):
                                metric_value_numeric = 0.0
                            try:
                                threshold_numeric = float(detail_threshold)
                            except (TypeError, ValueError):
                                threshold_numeric = 0.0
                            audit.rule_triggered(
                                tenant_id,
                                str(rule_id),
                                rule["name"],
                                device_id,
                                detail_metric,
                                metric_value_numeric,
                                threshold_numeric,
                                detail_operator,
                            )
                            if inserted:
                                log_event(
                                    logger,
                                    "alert created",
                                    tenant_id=tenant_id,
                                    device_id=device_id,
                                    alert_type="THRESHOLD",
                                    alert_id=str(alert_id),
                                    fingerprint=fp_rule,
                                )
                                audit.alert_created(
                                    tenant_id,
                                    str(alert_id),
                                    "THRESHOLD",
                                    device_id,
                                    summary,
                                )

                total_rules = sum(len(v) for v in tenant_rules_cache.values())
                log_event(
                    logger,
                    "evaluation cycle complete",
                    device_count=len(rows),
                    rule_count=total_rules,
                    tenant_count=len(tenant_rules_cache),
                )
                COUNTERS["last_evaluation_at"] = now_utc().isoformat()

                current_monotonic = time.monotonic()
                if current_monotonic - last_escalation_check > 60:
                    escalated = await check_escalations(pool)
                    if escalated > 0:
                        log_event(logger, "escalation check", escalated=escalated)
                    last_escalation_check = current_monotonic
                if conn is not None:
                    await pool.release(conn)

                eval_duration = time.monotonic() - eval_start
                pulse_processing_duration_seconds.labels(
                    service="evaluator",
                    operation="evaluation_cycle",
                ).observe(eval_duration)

                pulse_db_pool_size.labels(service="evaluator").set(pool.get_size())
                pulse_db_pool_free.labels(service="evaluator").set(pool.get_idle_size())
                log_event(logger, "tick_done", tick="evaluator")
            except Exception as exc:
                if conn is not None:
                    with contextlib.suppress(Exception):
                        await pool.release(conn)
                COUNTERS["evaluation_errors"] += 1
                evaluator_evaluation_errors_total.inc()
                logger.error(
                    "evaluation loop failed",
                    extra={"error_type": type(exc).__name__, "error": str(exc)},
                    exc_info=True,
                )
                await asyncio.sleep(1)
            finally:
                trace_id_var.reset(trace_token)
    finally:
        stop_listener.set()
        listener_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await listener_task

if __name__ == "__main__":
    asyncio.run(main())
