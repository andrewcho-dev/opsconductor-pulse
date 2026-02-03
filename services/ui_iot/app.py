import os
import base64
import hashlib
import logging
import secrets
import time
import asyncpg
import httpx
from urllib.parse import urlparse, urlencode
from fastapi import FastAPI, Form, Query, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from starlette.requests import Request

from routes.customer import router as customer_router
from routes.operator import router as operator_router
from middleware.auth import validate_token

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
app.mount("/static", StaticFiles(directory="static"), name="static")

app.include_router(customer_router)
app.include_router(operator_router)

pool: asyncpg.Pool | None = None

logger = logging.getLogger(__name__)


def _secure_cookies_enabled() -> bool:
    return os.getenv("SECURE_COOKIES", "false").lower() == "true"


def get_ui_base_url() -> str:
    return os.getenv("UI_BASE_URL", "http://localhost:8080").rstrip("/")


def generate_pkce_pair() -> tuple[str, str]:
    verifier = secrets.token_urlsafe(32)
    challenge = base64.urlsafe_b64encode(
        hashlib.sha256(verifier.encode()).digest()
    ).rstrip(b"=").decode()
    return verifier, challenge


def generate_state() -> str:
    return secrets.token_urlsafe(32)

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

    # Log URL configuration for debugging OAuth issues
    keycloak_public = _get_keycloak_public_url()
    keycloak_internal = _get_keycloak_internal_url()
    ui_base = get_ui_base_url()
    logger.info("OAuth config: KEYCLOAK_PUBLIC_URL=%s KEYCLOAK_INTERNAL_URL=%s UI_BASE_URL=%s",
                keycloak_public, keycloak_internal, ui_base)

    # Warn if public URLs use different hostnames (common misconfiguration)
    kc_host = urlparse(keycloak_public).hostname
    ui_host = urlparse(ui_base).hostname
    if kc_host != ui_host:
        logger.warning(
            "HOSTNAME MISMATCH: Keycloak public hostname (%s) != UI hostname (%s). "
            "OAuth login will fail because cookies are domain-scoped. "
            "Set KEYCLOAK_URL and UI_BASE_URL to use the same hostname.",
            kc_host, ui_host,
        )

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

def get_callback_url() -> str:
    return f"{get_ui_base_url()}/callback"


def _get_keycloak_public_url() -> str:
    return (os.getenv("KEYCLOAK_PUBLIC_URL") or os.getenv("KEYCLOAK_URL", "http://localhost:8180")).rstrip("/")


def _get_keycloak_internal_url() -> str:
    return (os.getenv("KEYCLOAK_INTERNAL_URL") or os.getenv("KEYCLOAK_URL", "http://localhost:8180")).rstrip("/")


def build_authorization_url(state: str, code_challenge: str) -> str:
    keycloak_url = _get_keycloak_public_url()
    realm = os.getenv("KEYCLOAK_REALM", "pulse")
    client_id = "pulse-ui"
    redirect_uri = get_callback_url()
    return (
        f"{keycloak_url}/realms/{realm}/protocol/openid-connect/auth"
        f"?client_id={client_id}"
        f"&response_type=code"
        f"&redirect_uri={redirect_uri}"
        f"&scope=openid"
        f"&state={state}"
        f"&code_challenge={code_challenge}"
        f"&code_challenge_method=S256"
    )


@app.get("/login")
async def login():
    verifier, challenge = generate_pkce_pair()
    state = generate_state()

    response = RedirectResponse(url=build_authorization_url(state, challenge), status_code=302)
    response.set_cookie(
        "oauth_state",
        state,
        httponly=True,
        secure=_secure_cookies_enabled(),
        samesite="lax",
        max_age=600,
        path="/",
    )
    response.set_cookie(
        "oauth_verifier",
        verifier,
        httponly=True,
        secure=_secure_cookies_enabled(),
        samesite="lax",
        max_age=600,
        path="/",
    )
    return response


@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    session_token = request.cookies.get("pulse_session")
    if not session_token:
        return RedirectResponse(url="/login", status_code=302)

    try:
        payload = await validate_token(session_token)
        role = payload.get("role", "")
        if role in ("operator", "operator_admin"):
            return RedirectResponse(url="/operator/dashboard", status_code=302)
        if role in ("customer_admin", "customer_viewer"):
            return RedirectResponse(url="/customer/dashboard", status_code=302)
        return RedirectResponse(url="/login", status_code=302)
    except Exception:
        return RedirectResponse(url="/login", status_code=302)


@app.get("/callback")
async def oauth_callback(request: Request, code: str | None = Query(None), state: str | None = Query(None)):
    if not code:
        return RedirectResponse(url="/?error=missing_code", status_code=302)

    stored_state = request.cookies.get("oauth_state")
    if not stored_state or not state:
        return RedirectResponse(url="/?error=missing_state", status_code=302)
    if state != stored_state:
        return RedirectResponse(url="/?error=state_mismatch", status_code=302)

    verifier = request.cookies.get("oauth_verifier")
    if not verifier:
        return RedirectResponse(url="/?error=missing_verifier", status_code=302)

    keycloak_url = _get_keycloak_internal_url()
    realm = os.getenv("KEYCLOAK_REALM", "pulse")
    token_url = f"{keycloak_url}/realms/{realm}/protocol/openid-connect/token"

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                token_url,
                data={
                    "grant_type": "authorization_code",
                    "client_id": "pulse-ui",
                    "code": code,
                    "redirect_uri": get_callback_url(),
                    "code_verifier": verifier,
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
    except httpx.RequestError:
        logger.exception("OAuth token exchange failed")
        raise HTTPException(status_code=503, detail="Auth service unavailable")

    if 500 <= response.status_code < 600:
        logger.error("OAuth token exchange server error: %s", response.text)
        raise HTTPException(status_code=503, detail="Auth service unavailable")
    if response.status_code >= 400:
        logger.warning("OAuth token exchange rejected: %s", response.text)
        return RedirectResponse(url="/?error=invalid_code", status_code=302)

    token_payload = response.json()
    access_token = token_payload.get("access_token")
    refresh_token = token_payload.get("refresh_token")
    expires_in = token_payload.get("expires_in", 0)
    if not access_token or not refresh_token:
        return RedirectResponse(url="/?error=invalid_code", status_code=302)

    try:
        validated = await validate_token(access_token)
    except Exception:
        return RedirectResponse(url="/?error=invalid_token", status_code=302)

    role = validated.get("role", "")
    if role in ("operator", "operator_admin"):
        redirect_url = "/operator/dashboard"
    elif role in ("customer_admin", "customer_viewer"):
        redirect_url = "/customer/dashboard"
    else:
        redirect_url = "/?error=unknown_role"

    redirect = RedirectResponse(url=redirect_url, status_code=302)
    redirect.delete_cookie("oauth_state", path="/")
    redirect.delete_cookie("oauth_verifier", path="/")
    redirect.set_cookie(
        "pulse_session",
        access_token,
        httponly=True,
        secure=_secure_cookies_enabled(),
        samesite="lax",
        max_age=int(expires_in),
        path="/",
    )
    redirect.set_cookie(
        "pulse_refresh",
        refresh_token,
        httponly=True,
        secure=_secure_cookies_enabled(),
        samesite="lax",
        max_age=1800,
        path="/",
    )
    return redirect


@app.get("/logout")
async def logout():
    keycloak_url = _get_keycloak_public_url()
    realm = os.getenv("KEYCLOAK_REALM", "pulse")
    redirect_uri = f"{get_ui_base_url()}/"
    query = urlencode(
        {
            "client_id": "pulse-ui",
            "post_logout_redirect_uri": redirect_uri,
        }
    )
    response = RedirectResponse(
        url=f"{keycloak_url}/realms/{realm}/protocol/openid-connect/logout?{query}",
        status_code=302,
    )
    response.delete_cookie("pulse_session", path="/")
    response.delete_cookie("pulse_refresh", path="/")
    return response


@app.get("/api/auth/status")
async def auth_status(request: Request):
    session_token = request.cookies.get("pulse_session")
    if not session_token:
        return {"authenticated": False}

    try:
        payload = await validate_token(session_token)
    except Exception:
        return {"authenticated": False}

    exp = payload.get("exp")
    expires_in = 0
    if exp:
        expires_in = max(0, int(exp - time.time()))

    return {
        "authenticated": True,
        "user": {
            "email": payload.get("email"),
            "role": payload.get("role"),
            "tenant_id": payload.get("tenant_id"),
        },
        "expires_in": expires_in,
    }


@app.post("/api/auth/refresh")
async def auth_refresh(request: Request):
    refresh_token = request.cookies.get("pulse_refresh")
    if not refresh_token:
        raise HTTPException(status_code=401, detail="Missing refresh token")

    keycloak_url = _get_keycloak_internal_url()
    realm = os.getenv("KEYCLOAK_REALM", "pulse")
    token_url = f"{keycloak_url}/realms/{realm}/protocol/openid-connect/token"

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                token_url,
                data={
                    "grant_type": "refresh_token",
                    "client_id": "pulse-ui",
                    "refresh_token": refresh_token,
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
    except httpx.RequestError:
        logger.exception("Token refresh failed")
        raise HTTPException(status_code=503, detail="Auth service unavailable")

    if response.status_code >= 400:
        cleared = JSONResponse({"success": False}, status_code=401)
        cleared.delete_cookie("pulse_session", path="/")
        cleared.delete_cookie("pulse_refresh", path="/")
        return cleared

    token_payload = response.json()
    access_token = token_payload.get("access_token")
    new_refresh_token = token_payload.get("refresh_token")
    expires_in = token_payload.get("expires_in", 300)
    refresh_expires_in = token_payload.get("refresh_expires_in", 1800)
    if not access_token or not new_refresh_token:
        cleared = JSONResponse({"success": False}, status_code=401)
        cleared.delete_cookie("pulse_session", path="/")
        cleared.delete_cookie("pulse_refresh", path="/")
        return cleared

    refreshed = JSONResponse({"success": True, "expires_in": expires_in})
    refreshed.set_cookie(
        "pulse_session",
        access_token,
        httponly=True,
        secure=_secure_cookies_enabled(),
        samesite="lax",
        max_age=int(expires_in),
        path="/",
    )
    refreshed.set_cookie(
        "pulse_refresh",
        new_refresh_token,
        httponly=True,
        secure=_secure_cookies_enabled(),
        samesite="lax",
        max_age=int(refresh_expires_in),
        path="/",
    )
    return refreshed


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
