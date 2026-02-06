"""InfluxDB query functions for telemetry and event data.

These replace the PostgreSQL event-table queries with InfluxDB equivalents.
Return formats match the PG versions exactly for template compatibility.
"""
import os
from datetime import datetime, timezone, timedelta

import httpx


INFLUXDB_URL = os.getenv("INFLUXDB_URL", "http://iot-influxdb:8181")
INFLUXDB_TOKEN = os.getenv("INFLUXDB_TOKEN", "influx-dev-token-change-me")
# Columns that are NOT device metrics — same set as evaluator's skip_keys
TELEMETRY_METADATA_KEYS = {"time", "device_id", "site_id", "seq"}


def _parse_influx_ts(val) -> datetime | None:
    """Parse a timestamp value from InfluxDB into a timezone-aware UTC datetime."""
    if val is None:
        return None
    if isinstance(val, datetime):
        return val
    if isinstance(val, (int, float)):
        return datetime.fromtimestamp(val / 1e9, tz=timezone.utc)
    if isinstance(val, str):
        try:
            clean = val.replace("Z", "+00:00")
            dt = datetime.fromisoformat(clean)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except Exception:
            return None
    return None


def extract_metrics(row: dict) -> dict:
    """Extract metric columns from an InfluxDB row, filtering out metadata.

    Filters time, device_id, site_id, seq, and InfluxDB internal columns (iox::*).
    Returns only actual device metrics like battery_pct, temp_c, pressure_psi, etc.
    """
    metrics = {}
    for k, v in row.items():
        if k in TELEMETRY_METADATA_KEYS or k.startswith("iox::"):
            continue
        if v is not None:
            metrics[k] = v
    return metrics


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
            return []

        data = resp.json()
        rows: list[dict] = []
        if isinstance(data, list):
            rows = data
        if isinstance(data, dict):
            if "results" in data:
                rows = data["results"]
            if "data" in data:
                rows = data["data"]
        return rows
    except Exception:
        return []


async def fetch_device_telemetry_influx(
    http_client: httpx.AsyncClient,
    tenant_id: str,
    device_id: str,
    limit: int = 120,
) -> list[dict]:
    """Fetch recent telemetry for a device from InfluxDB.

    Returns format matching PG version:
    [{"ingested_at": datetime, "battery_pct": float|None, "temp_c": float|None, "rssi_dbm": int|None}, ...]
    """
    db_name = f"telemetry_{tenant_id}"
    sql = (
        f"SELECT time, battery_pct, temp_c, rssi_dbm "
        f"FROM telemetry "
        f"WHERE device_id = '{device_id}' "
        f"ORDER BY time DESC "
        f"LIMIT {limit}"
    )

    rows = await _influx_query(http_client, db_name, sql)
    results = []
    for row in rows:
        rssi = row.get("rssi_dbm")
        results.append({
            "ingested_at": _parse_influx_ts(row.get("time")),
            "battery_pct": row.get("battery_pct"),
            "temp_c": row.get("temp_c"),
            "rssi_dbm": int(rssi) if rssi is not None else None,
        })
    return results


async def fetch_device_events_influx(
    http_client: httpx.AsyncClient,
    tenant_id: str,
    device_id: str,
    limit: int = 50,
) -> list[dict]:
    """Fetch recent events (heartbeat + telemetry) for a device from InfluxDB.

    Returns format matching PG version:
    [{"ingested_at": datetime, "accepted": True, "tenant_id": str, "site_id": None,
      "msg_type": str, "reject_reason": None}, ...]

    Note: InfluxDB only has accepted events. Rejected events stay in PG quarantine.
    """
    db_name = f"telemetry_{tenant_id}"

    # Query heartbeats
    hb_sql = (
        f"SELECT time, 'heartbeat' AS msg_type "
        f"FROM heartbeat "
        f"WHERE device_id = '{device_id}' "
        f"ORDER BY time DESC "
        f"LIMIT {limit}"
    )

    # Query telemetry
    tel_sql = (
        f"SELECT time, 'telemetry' AS msg_type "
        f"FROM telemetry "
        f"WHERE device_id = '{device_id}' "
        f"ORDER BY time DESC "
        f"LIMIT {limit}"
    )

    hb_rows = await _influx_query(http_client, db_name, hb_sql)
    tel_rows = await _influx_query(http_client, db_name, tel_sql)

    # Merge and sort by time descending
    all_events = []
    for row in hb_rows:
        ts = _parse_influx_ts(row.get("time"))
        all_events.append({
            "ingested_at": ts,
            "accepted": True,
            "tenant_id": tenant_id,
            "site_id": None,
            "msg_type": "heartbeat",
            "reject_reason": None,
        })
    for row in tel_rows:
        ts = _parse_influx_ts(row.get("time"))
        all_events.append({
            "ingested_at": ts,
            "accepted": True,
            "tenant_id": tenant_id,
            "site_id": None,
            "msg_type": "telemetry",
            "reject_reason": None,
        })

    # Sort by time descending, take first `limit`
    all_events.sort(
        key=lambda e: e["ingested_at"] or datetime.min.replace(tzinfo=timezone.utc),
        reverse=True,
    )
    return all_events[:limit]


async def fetch_device_telemetry_dynamic(
    http_client: httpx.AsyncClient,
    tenant_id: str,
    device_id: str,
    start: str | None = None,
    end: str | None = None,
    limit: int = 120,
) -> list[dict]:
    """Fetch device telemetry with ALL metric columns dynamically.

    Unlike fetch_device_telemetry_influx (which hardcodes 3 metrics), this
    uses SELECT * and filters metadata columns, returning all device metrics.

    Returns: [{"timestamp": "2024-...", "metrics": {"battery_pct": 87.5, ...}}, ...]
    """
    db_name = f"telemetry_{tenant_id}"

    where_parts = [f"device_id = '{device_id}'"]
    if not start:
        start = (datetime.now(timezone.utc) - timedelta(hours=6)).isoformat()
    if start:
        where_parts.append(f"time >= '{start}'")
    if end:
        where_parts.append(f"time <= '{end}'")

    where_sql = " AND ".join(where_parts)
    sql = f"SELECT * FROM telemetry WHERE {where_sql} ORDER BY time DESC LIMIT {limit}"
    rows = await _influx_query(http_client, db_name, sql)

    results = []
    for row in rows:
        ts = _parse_influx_ts(row.get("time"))
        metrics = extract_metrics(row)
        results.append({
            "timestamp": ts.isoformat() if ts else None,
            "metrics": metrics,
        })
    return results
