import os
import sys
sys.path.insert(0, "/app")
import base64
import hashlib
import logging
import secrets
import time
import asyncpg
import httpx
from pathlib import Path
from urllib.parse import urlparse, urlencode
from fastapi import FastAPI, Query, HTTPException
from fastapi.responses import RedirectResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from starlette.requests import Request
from starlette.middleware.cors import CORSMiddleware

from routes.customer import router as customer_router
from routes.operator import router as operator_router
from routes.system import router as system_router
from routes.api_v2 import router as api_v2_router, ws_router as api_v2_ws_router
from routes.ingest import router as ingest_router
from middleware.auth import validate_token
from shared.ingest_core import DeviceAuthCache, TimescaleBatchWriter
from metrics_collector import collector

PG_HOST = os.getenv("PG_HOST", "iot-postgres")
PG_PORT = int(os.getenv("PG_PORT", "5432"))
PG_DB   = os.getenv("PG_DB", "iotcloud")
PG_USER = os.getenv("PG_USER", "iot")
PG_PASS = os.getenv("PG_PASS", "iot_dev")

AUTH_CACHE_TTL = int(os.getenv("AUTH_CACHE_TTL_SECONDS", "60"))
BATCH_SIZE = int(os.getenv("BATCH_SIZE", "500"))
FLUSH_INTERVAL_MS = int(os.getenv("FLUSH_INTERVAL_MS", "1000"))
REQUIRE_TOKEN = os.getenv("REQUIRE_TOKEN", "1") == "1"

UI_REFRESH_SECONDS = int(os.getenv("UI_REFRESH_SECONDS", "5"))

CORS_ALLOWED_ORIGINS = os.getenv("CORS_ALLOWED_ORIGINS", "*")

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ALLOWED_ORIGINS.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(customer_router)
app.include_router(operator_router)
app.include_router(system_router)
app.include_router(api_v2_router)
app.include_router(api_v2_ws_router)
app.include_router(ingest_router)

# React SPA — serve built frontend if available
SPA_DIR = Path("/app/spa")
if SPA_DIR.exists() and (SPA_DIR / "index.html").exists():
    # Serve static assets (JS, CSS, images) from /app/assets/
    app.mount("/app/assets", StaticFiles(directory=str(SPA_DIR / "assets")), name="spa-assets")

    @app.get("/app/{path:path}")
    async def spa_catchall(path: str):
        """Serve React SPA — all /app/* routes return index.html for client-side routing."""
        file = SPA_DIR / path
        if file.is_file() and ".." not in path:
            return FileResponse(str(file))
        return FileResponse(str(SPA_DIR / "index.html"))

    @app.get("/app")
    async def spa_root():
        """Serve React SPA root."""
        return FileResponse(str(SPA_DIR / "index.html"))

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    if exc.status_code == 401:
        accept = request.headers.get("accept", "")
        if "text/html" in accept:
            return RedirectResponse(url="/", status_code=302)
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})

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

    # Initialize HTTP ingest infrastructure
    app.state.get_pool = get_pool
    app.state.auth_cache = DeviceAuthCache(ttl_seconds=AUTH_CACHE_TTL)
    pool = await get_pool()
    app.state.batch_writer = TimescaleBatchWriter(
        pool=pool,
        batch_size=BATCH_SIZE,
        flush_interval_ms=FLUSH_INTERVAL_MS,
    )
    await app.state.batch_writer.start()
    app.state.rate_buckets = {}
    app.state.max_payload_bytes = 8192
    app.state.rps = 5.0
    app.state.burst = 20.0
    app.state.require_token = REQUIRE_TOKEN

    await collector.start()

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


@app.on_event("shutdown")
async def shutdown():
    await collector.stop()
    if hasattr(app.state, "batch_writer"):
        await app.state.batch_writer.stop()

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

@app.get("/api/v2/health")
async def api_v2_health():
    return {"status": "ok", "service": "pulse-ui", "api_version": "v2"}

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


@app.get("/")
async def root():
    return RedirectResponse(url="/app/", status_code=302)


@app.get("/callback")
async def oauth_callback(request: Request, code: str | None = Query(None), state: str | None = Query(None)):
    if not code:
        return RedirectResponse(url="/?error=missing_code", status_code=302)

    stored_state = request.cookies.get("oauth_state")
    if not stored_state or not state:
        logger.warning(
            "OAuth callback: missing state cookie. Browser host: %s, cookies present: %s",
            request.headers.get("host"),
            list(request.cookies.keys()),
        )
        return RedirectResponse(url="/?error=missing_state", status_code=302)
    if state != stored_state:
        logger.warning(
            "OAuth callback: state mismatch. Expected cookie value, got query param: %s",
            state[:8] + "...",
        )
        return RedirectResponse(url="/?error=state_mismatch", status_code=302)

    verifier = request.cookies.get("oauth_verifier")
    if not verifier:
        logger.warning(
            "OAuth callback: missing verifier cookie. Browser host: %s",
            request.headers.get("host"),
        )
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
        logger.warning(
            "OAuth token exchange rejected (HTTP %s): %s",
            response.status_code,
            response.text[:200],
        )
        return RedirectResponse(url="/?error=invalid_code", status_code=302)

    token_payload = response.json()
    access_token = token_payload.get("access_token")
    refresh_token = token_payload.get("refresh_token")
    expires_in = token_payload.get("expires_in", 0)
    if not access_token or not refresh_token:
        return RedirectResponse(url="/?error=invalid_code", status_code=302)

    try:
        validated = await validate_token(access_token)
    except Exception as e:
        logger.warning("OAuth callback: token validation failed: %s", str(e))
        return RedirectResponse(url="/?error=invalid_token", status_code=302)

    redirect_url = "/app/"

    redirect = RedirectResponse(url=redirect_url, status_code=302)
    redirect.delete_cookie("oauth_state", path="/")
    redirect.delete_cookie("oauth_verifier", path="/")
    redirect.set_cookie(
        "pulse_session",
        access_token,
        httponly=True,
        secure=_secure_cookies_enabled(),
        samesite="lax",
        max_age=int(expires_in) + 60,
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
        max_age=int(expires_in) + 60,
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


@app.get("/debug/auth")
async def debug_auth(request: Request):
    """Diagnostic endpoint for OAuth configuration (DEV only)."""
    mode = os.getenv("MODE", "DEV").upper()
    if mode != "DEV":
        raise HTTPException(status_code=404, detail="Not found")

    keycloak_public = _get_keycloak_public_url()
    keycloak_internal = _get_keycloak_internal_url()
    ui_base = get_ui_base_url()
    callback = get_callback_url()

    kc_host = urlparse(keycloak_public).hostname
    ui_host = urlparse(ui_base).hostname

    # Check if Keycloak is reachable internally
    keycloak_reachable = False
    keycloak_issuer = None
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            r = await client.get(
                f"{keycloak_internal}/realms/{os.getenv('KEYCLOAK_REALM', 'pulse')}/.well-known/openid-configuration"
            )
            if r.status_code == 200:
                keycloak_reachable = True
                keycloak_issuer = r.json().get("issuer")
    except Exception:
        keycloak_reachable = False

    expected_issuer = f"{keycloak_public}/realms/{os.getenv('KEYCLOAK_REALM', 'pulse')}"

    # Check cookies
    has_session = "pulse_session" in request.cookies
    has_refresh = "pulse_refresh" in request.cookies
    has_state = "oauth_state" in request.cookies
    has_verifier = "oauth_verifier" in request.cookies

    # Browser info
    host_header = request.headers.get("host", "unknown")
    origin = request.headers.get("origin", "none")
    forwarded = request.headers.get("x-forwarded-for", "none")

    hostname_match = kc_host == ui_host
    issuer_match = keycloak_issuer == expected_issuer if keycloak_issuer else None

    return {
        "status": "ok" if (hostname_match and keycloak_reachable and issuer_match) else "MISCONFIGURED",
        "urls": {
            "keycloak_public": keycloak_public,
            "keycloak_internal": keycloak_internal,
            "ui_base": ui_base,
            "callback": callback,
        },
        "hostname_check": {
            "keycloak_hostname": kc_host,
            "ui_hostname": ui_host,
            "match": hostname_match,
            "verdict": "OK" if hostname_match else "FAIL: cookies will be lost across domains",
        },
        "keycloak_check": {
            "reachable": keycloak_reachable,
            "actual_issuer": keycloak_issuer,
            "expected_issuer": expected_issuer,
            "issuer_match": issuer_match,
            "verdict": (
                "OK" if issuer_match
                else "FAIL: token iss claim won't match validator" if keycloak_issuer
                else "FAIL: Keycloak unreachable"
            ),
        },
        "cookies": {
            "pulse_session": has_session,
            "pulse_refresh": has_refresh,
            "oauth_state": has_state,
            "oauth_verifier": has_verifier,
        },
        "request": {
            "host_header": host_header,
            "origin": origin,
            "x_forwarded_for": forwarded,
        },
    }


