import os
import asyncpg
import httpx
from urllib.parse import urlparse
from fastapi import FastAPI, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from starlette.requests import Request

PG_HOST = os.getenv("PG_HOST", "iot-postgres")
PG_PORT = int(os.getenv("PG_PORT", "5432"))
PG_DB   = os.getenv("PG_DB", "iotcloud")
PG_USER = os.getenv("PG_USER", "iot")
PG_PASS = os.getenv("PG_PASS", "iot_dev")

UI_REFRESH_SECONDS = int(os.getenv("UI_REFRESH_SECONDS", "5"))

PROVISION_API_URL = os.getenv("PROVISION_API_URL", "http://iot-api:8081")
PROVISION_ADMIN_KEY = os.getenv("PROVISION_ADMIN_KEY", "change-me-now")

app = FastAPI()
templates = Jinja2Templates(directory="/app/templates")

pool: asyncpg.Pool | None = None

def to_float(v):
    try:
        if v is None:
            return None
        return float(v)
    except Exception:
        return None

def to_int(v):
    try:
        if v is None:
            return None
        return int(v)
    except Exception:
        return None

def sparkline_points(values, width=520, height=60, pad=4):
    vals = [v for v in values if v is not None]
    if len(vals) < 2:
        return ""
    vmin = min(vals)
    vmax = max(vals)
    if vmax == vmin:
        vmax = vmin + 1.0

    n = len(values)

    def x(i):
        return pad + (i * (width - 2 * pad) / max(1, n - 1))

    pts = []
    for i, v in enumerate(values):
        if v is None:
            continue
        y = pad + (height - 2 * pad) * (1.0 - ((v - vmin) / (vmax - vmin)))
        pts.append(f"{x(i):.1f},{y:.1f}")
    return " ".join(pts)

def redact_url(value: str | None) -> str:
    if not value:
        return ""
    try:
        parsed = urlparse(value)
    except Exception:
        return ""
    if not parsed.hostname:
        return ""
    scheme = parsed.scheme or "http"
    port = f":{parsed.port}" if parsed.port else ""
    return f"{scheme}://{parsed.hostname}{port}"

async def get_pool():
    global pool
    if pool is None:
        pool = await asyncpg.create_pool(
            host=PG_HOST, port=PG_PORT, database=PG_DB,
            user=PG_USER, password=PG_PASS,
            min_size=1, max_size=5
        )
    return pool

@app.on_event("startup")
async def startup():
    await get_pool()

async def get_settings(conn):
    rows = await conn.fetch(
        "SELECT key, value FROM app_settings WHERE key IN "
        "('MODE','STORE_REJECTS','MIRROR_REJECTS_TO_RAW','RATE_LIMIT_RPS','RATE_LIMIT_BURST','MAX_PAYLOAD_BYTES')"
    )
    kv = {r["key"]: r["value"] for r in rows}

    mode = (kv.get("MODE", "PROD") or "PROD").upper()
    if mode not in ("PROD", "DEV"):
        mode = "PROD"

    store_rejects = kv.get("STORE_REJECTS", "0")
    mirror_rejects = kv.get("MIRROR_REJECTS_TO_RAW", "0")

    # Policy lock in PROD
    if mode == "PROD":
        store_rejects = "0"
        mirror_rejects = "0"

    rate_rps = kv.get("RATE_LIMIT_RPS", "5")
    rate_burst = kv.get("RATE_LIMIT_BURST", "20")
    max_payload_bytes = kv.get("MAX_PAYLOAD_BYTES", "8192")

    return mode, store_rejects, mirror_rejects, rate_rps, rate_burst, max_payload_bytes

@app.post("/settings")
async def update_settings(
    mode: str = Form("PROD"),
    store_rejects: str = Form("0"),
    mirror_rejects: str = Form("0"),
):
    mode = (mode or "PROD").upper()
    if mode not in ("PROD", "DEV"):
        mode = "PROD"

    if mode == "PROD":
        store_rejects = "0"
        mirror_rejects = "0"

    p = await get_pool()
    async with p.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO app_settings (key, value, updated_at)
            VALUES ('MODE', $1, now())
            ON CONFLICT (key) DO UPDATE SET value=EXCLUDED.value, updated_at=now();
            """,
            mode
        )
        await conn.execute(
            """
            INSERT INTO app_settings (key, value, updated_at)
            VALUES ('STORE_REJECTS', $1, now())
            ON CONFLICT (key) DO UPDATE SET value=EXCLUDED.value, updated_at=now();
            """,
            "1" if store_rejects == "1" else "0"
        )
        await conn.execute(
            """
            INSERT INTO app_settings (key, value, updated_at)
            VALUES ('MIRROR_REJECTS_TO_RAW', $1, now())
            ON CONFLICT (key) DO UPDATE SET value=EXCLUDED.value, updated_at=now();
            """,
            "1" if mirror_rejects == "1" else "0"
        )

    return RedirectResponse(url="/", status_code=303)

@app.post("/admin/create-device")
async def admin_create_device(
    tenant_id: str = Form(...),
    device_id: str = Form(...),
    site_id: str = Form(...),
    fw_version: str = Form(""),
):
    payload = {
        "tenant_id": tenant_id.strip(),
        "device_id": device_id.strip(),
        "site_id": site_id.strip(),
        "fw_version": fw_version.strip() or None,
        "metadata": {"created_via": "ui"},
    }
    headers = {"X-Admin-Key": PROVISION_ADMIN_KEY}
    async with httpx.AsyncClient(timeout=10.0) as client:
        r = await client.post(f"{PROVISION_API_URL}/api/admin/devices", headers=headers, json=payload)
        if r.status_code != 200:
            return RedirectResponse(url="/?admin_err=create_failed", status_code=303)
    # Store the last response in app_settings for display (simple demo approach)
    p = await get_pool()
    async with p.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO app_settings (key, value, updated_at)
            VALUES ('LAST_ADMIN_CREATE', $1, now())
            ON CONFLICT (key) DO UPDATE SET value=EXCLUDED.value, updated_at=now();
            """,
            r.text
        )
    return RedirectResponse(url="/", status_code=303)

@app.post("/admin/activate-device")
async def admin_activate_device(
    tenant_id: str = Form(...),
    device_id: str = Form(...),
    activation_code: str = Form(...),
):
    payload = {
        "tenant_id": tenant_id.strip(),
        "device_id": device_id.strip(),
        "activation_code": activation_code.strip(),
    }
    async with httpx.AsyncClient(timeout=10.0) as client:
        r = await client.post(f"{PROVISION_API_URL}/api/device/activate", json=payload)
        if r.status_code != 200:
            return RedirectResponse(url="/?admin_err=activate_failed", status_code=303)

    p = await get_pool()
    async with p.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO app_settings (key, value, updated_at)
            VALUES ('LAST_DEVICE_ACTIVATE', $1, now())
            ON CONFLICT (key) DO UPDATE SET value=EXCLUDED.value, updated_at=now();
            """,
            r.text
        )
    return RedirectResponse(url="/", status_code=303)

@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    p = await get_pool()
    async with p.acquire() as conn:
        mode, store_rejects, mirror_rejects, rate_rps, rate_burst, max_payload_bytes = await get_settings(conn)

        last_create = await conn.fetchval("SELECT value FROM app_settings WHERE key='LAST_ADMIN_CREATE'") or ""
        last_activate = await conn.fetchval("SELECT value FROM app_settings WHERE key='LAST_DEVICE_ACTIVATE'") or ""

        devices = await conn.fetch(
            """
            SELECT tenant_id, site_id, device_id, status, last_seen_at,
                   state->>'battery_pct' AS battery_pct,
                   state->>'temp_c' AS temp_c,
                   state->>'rssi_dbm' AS rssi_dbm,
                   state->>'snr_db' AS snr_db
            FROM device_state
            ORDER BY tenant_id, site_id, device_id
            """
        )

        open_alerts = await conn.fetch(
            """
            SELECT created_at, tenant_id, site_id, device_id, alert_type, severity, confidence, summary
            FROM fleet_alert
            WHERE status='OPEN'
            ORDER BY created_at DESC
            LIMIT 200
            """
        )

        integrations_rows = await conn.fetch(
            """
            SELECT tenant_id, integration_id, name, enabled, config_json->>'url' AS url, created_at
            FROM integrations
            ORDER BY created_at DESC
            LIMIT 200
            """
        )
        integrations = [
            {
                "tenant_id": r["tenant_id"],
                "integration_id": str(r["integration_id"]),
                "name": r["name"],
                "enabled": r["enabled"],
                "url": redact_url(r["url"]),
                "created_at": r["created_at"],
            }
            for r in integrations_rows
        ]

        delivery_attempt_rows = await conn.fetch(
            """
            SELECT tenant_id, job_id, attempt_no, ok, http_status, latency_ms, error, finished_at
            FROM delivery_attempts
            ORDER BY finished_at DESC
            LIMIT 20
            """
        )
        delivery_attempts = [
            {
                "tenant_id": r["tenant_id"],
                "job_id": r["job_id"],
                "attempt_no": r["attempt_no"],
                "ok": r["ok"],
                "http_status": r["http_status"],
                "latency_ms": r["latency_ms"],
                "error": r["error"],
                "finished_at": r["finished_at"],
            }
            for r in delivery_attempt_rows
        ]

        quarantine = await conn.fetch(
            """
            SELECT ingested_at, tenant_id, site_id, device_id, msg_type, reason
            FROM quarantine_events
            ORDER BY ingested_at DESC
            LIMIT 50
            """
        )

        counts = await conn.fetchrow(
            """
            SELECT
              (SELECT COUNT(*) FROM device_state) AS devices_total,
              (SELECT COUNT(*) FROM device_state WHERE status='ONLINE') AS devices_online,
              (SELECT COUNT(*) FROM device_state WHERE status='STALE') AS devices_stale,
              (SELECT COUNT(*) FROM fleet_alert WHERE status='OPEN') AS alerts_open,
              (SELECT COUNT(*) FROM quarantine_events WHERE ingested_at > (now() - interval '10 minutes')) AS quarantined_10m
            """
        )

        rate_limited_10m = await conn.fetchval(
            """
            SELECT COALESCE(SUM(cnt),0)
            FROM quarantine_counters_minute
            WHERE reason='RATE_LIMITED'
              AND bucket_minute > (date_trunc('minute', now()) - interval '10 minutes')
            """
        )

        rate_limited_5m = await conn.fetchval(
            """
            SELECT COALESCE(SUM(cnt),0)
            FROM quarantine_counters_minute
            WHERE reason='RATE_LIMITED'
              AND bucket_minute > (date_trunc('minute', now()) - interval '5 minutes')
            """
        )

        reason_counts_10m = await conn.fetch(
            """
            SELECT reason, SUM(cnt) AS cnt
            FROM quarantine_counters_minute
            WHERE bucket_minute > (date_trunc('minute', now()) - interval '10 minutes')
            GROUP BY reason
            ORDER BY cnt DESC, reason ASC
            LIMIT 20
            """
        )

        rate_series = await conn.fetch(
            """
            SELECT bucket_minute, SUM(cnt) AS total_cnt,
                   COALESCE(SUM(cnt) FILTER (WHERE reason='RATE_LIMITED'),0) AS rate_limited_cnt
            FROM quarantine_counters_minute
            WHERE bucket_minute > (date_trunc('minute', now()) - interval '60 minutes')
            GROUP BY bucket_minute
            ORDER BY bucket_minute ASC
            """
        )
        series = [{"t": str(r["bucket_minute"]), "cnt": int(r["total_cnt"]), "rl": int(r["rate_limited_cnt"])} for r in rate_series]
        max_cnt = max([x["cnt"] for x in series], default=0)

    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "refresh": UI_REFRESH_SECONDS,
            "mode": mode,
            "store_rejects": store_rejects,
            "mirror_rejects": mirror_rejects,
            "rate_rps": rate_rps,
            "rate_burst": rate_burst,
            "max_payload_bytes": max_payload_bytes,
            "rate_limited_10m": int(rate_limited_10m or 0),
            "rate_limited_5m": int(rate_limited_5m or 0),
            "counts": counts,
            "devices": devices,
            "open_alerts": open_alerts,
            "integrations": integrations,
            "delivery_attempts": delivery_attempts,
            "quarantine": quarantine,
            "reason_counts_10m": reason_counts_10m,
            "rate_series": series,
            "rate_max": max_cnt,
            "last_create": last_create,
            "last_activate": last_activate,
        }
    )

@app.get("/device/{device_id}", response_class=HTMLResponse)
async def device_detail(request: Request, device_id: str):
    p = await get_pool()
    async with p.acquire() as conn:
        dev = await conn.fetchrow(
            """
            SELECT tenant_id, site_id, device_id, status, last_seen_at,
                   state->>'battery_pct' AS battery_pct,
                   state->>'temp_c' AS temp_c,
                   state->>'rssi_dbm' AS rssi_dbm,
                   state->>'snr_db' AS snr_db
            FROM device_state
            WHERE device_id=$1
            ORDER BY tenant_id
            LIMIT 1
            """,
            device_id
        )

        events = await conn.fetch(
            """
            SELECT ingested_at, accepted, tenant_id, site_id, msg_type,
                   payload->>'_reject_reason' AS reject_reason,
                   payload->>'provision_token' AS token
            FROM raw_events
            WHERE device_id=$1
            ORDER BY ingested_at DESC
            LIMIT 200
            """,
            device_id
        )

        series = await conn.fetch(
            """
            SELECT ingested_at,
                   (payload->'metrics'->>'battery_pct')::float AS battery_pct,
                   (payload->'metrics'->>'temp_c')::float AS temp_c,
                   (payload->'metrics'->>'rssi_dbm')::int   AS rssi_dbm
            FROM raw_events
            WHERE device_id=$1 AND msg_type='telemetry' AND accepted=true
            ORDER BY ingested_at DESC
            LIMIT 120
            """,
            device_id
        )

    series = list(reversed(series))
    bat = [to_float(r["battery_pct"]) for r in series]
    tmp = [to_float(r["temp_c"]) for r in series]
    rssi = [to_int(r["rssi_dbm"]) for r in series]
    rssi_f = [float(x) if x is not None else None for x in rssi]

    charts = {
        "battery_pts": sparkline_points(bat),
        "temp_pts": sparkline_points(tmp),
        "rssi_pts": sparkline_points(rssi_f),
    }

    return templates.TemplateResponse(
        "device.html",
        {
            "request": request,
            "refresh": UI_REFRESH_SECONDS,
            "device_id": device_id,
            "dev": dev,
            "events": events,
            "charts": charts,
        }
    )
