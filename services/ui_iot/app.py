import os
import asyncpg
import httpx
from urllib.parse import urlparse
from fastapi import FastAPI, Form, Query
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from starlette.requests import Request

from routes.customer import router as customer_router
from routes.operator import router as operator_router
from middleware.auth import JWTBearer, validate_token
from middleware.tenant import get_user, is_operator

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

app.include_router(customer_router)
app.include_router(operator_router)

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
async def settings_redirect():
    return RedirectResponse(url="/operator/settings", status_code=307)

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

def get_login_url():
    keycloak_url = os.getenv("KEYCLOAK_URL", "http://localhost:8180")
    realm = os.getenv("KEYCLOAK_REALM", "pulse")
    client_id = "pulse-ui"
    redirect_uri = "http://localhost:8080/callback"
    return (
        f"{keycloak_url}/realms/{realm}/protocol/openid-connect/auth"
        f"?client_id={client_id}"
        f"&response_type=code"
        f"&redirect_uri={redirect_uri}"
        f"&scope=openid"
    )


@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    auth_header = request.headers.get("Authorization", "")

    if not auth_header.startswith("Bearer "):
        return RedirectResponse(url=get_login_url(), status_code=302)

    try:
        token = auth_header[7:]
        payload = await validate_token(token)
        role = payload.get("role", "")

        if role in ("operator", "operator_admin"):
            return RedirectResponse(url="/operator/dashboard", status_code=302)
        if role in ("customer_admin", "customer_viewer"):
            return RedirectResponse(url="/customer/dashboard", status_code=302)
        return RedirectResponse(url=get_login_url(), status_code=302)
    except Exception:
        return RedirectResponse(url=get_login_url(), status_code=302)


@app.get("/callback")
async def oauth_callback(code: str = Query(...)):
    return RedirectResponse(url=f"/?code={code}", status_code=302)


@app.get("/logout")
async def logout():
    keycloak_url = os.getenv("KEYCLOAK_URL", "http://localhost:8180")
    realm = os.getenv("KEYCLOAK_REALM", "pulse")
    redirect_uri = "http://localhost:8080/"
    return RedirectResponse(
        url=f"{keycloak_url}/realms/{realm}/protocol/openid-connect/logout?redirect_uri={redirect_uri}",
        status_code=302,
    )


@app.get("/device/{device_id}", response_class=HTMLResponse)
async def device_detail_deprecated(request: Request, device_id: str):
    return HTMLResponse(
        content="""
        <html>
        <head><title>410 Gone</title></head>
        <body>
        <h1>410 Gone</h1>
        <p>This endpoint is deprecated.</p>
        <p>Use one of:</p>
        <ul>
            <li><code>/customer/devices/{device_id}</code> — for customers (requires login)</li>
            <li><code>/operator/tenants/{tenant_id}/devices/{device_id}</code> — for operators</li>
        </ul>
        <p><a href="/">Go to login</a></p>
        </body>
        </html>
        """,
        status_code=410,
    )
