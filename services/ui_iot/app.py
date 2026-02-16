import os
import asyncio
import base64
import hashlib
import logging
import secrets
import time
import uuid
import asyncpg
import httpx
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
from pathlib import Path
from urllib.parse import urlparse, urlencode
from fastapi import FastAPI, Query, HTTPException
from fastapi.responses import RedirectResponse, JSONResponse, FileResponse, Response
from fastapi.staticfiles import StaticFiles
from starlette.requests import Request
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from middleware.trace import TraceMiddleware

from routes.customer import router as customer_router, limiter
from routes.devices import router as devices_router
from routes.alerts import router as alerts_router
from routes.metrics import router as metrics_router
from routes.exports import router as exports_router
from routes.operator import router as operator_router
from routes.system import (
    router as system_router,
)
from routes.api_v2 import (
    router as api_v2_router,
    ws_router as api_v2_ws_router,
    setup_ws_listener,
    shutdown_ws_listener,
)
from routes.ingest import router as ingest_router
from routes.users import router as users_router
from routes.roles import router as roles_router
from routes.escalation import router as escalation_router
from routes.notifications import router as notifications_router
from routes.oncall import router as oncall_router
from routes.jobs import router as jobs_router
from middleware.auth import validate_token
from shared.ingest_core import DeviceAuthCache, TimescaleBatchWriter
from shared.audit import init_audit_logger
from shared.http_client import traced_client
from shared.logging import configure_logging
from shared.jwks_cache import init_jwks_cache, get_jwks_cache
from shared.metrics import fleet_active_alerts, fleet_devices_by_status

# PHASE 43 AUDIT — Background Tasks
#
# Task 1: health_monitor
#   - Interval: max(5s, HEALTH_CHECK_INTERVAL), default 60s
#   - What it does: polls ingest/evaluator/dispatcher/delivery health endpoints,
#     opens/closes system alerts based on service status transitions.
#   - Tables it writes: fleet_alert (OPEN/CLOSED system-health rows), tenants
#     (ensures synthetic __system__ tenant exists when opening alerts).
#   - External dependencies: HTTP calls to service /health endpoints.
#   - Decision: EXTRACT to ops_worker
#   - Reason: polling + alert maintenance is process-isolated work and does not
#     depend on request context.
#
# Task 2: metrics_collector
#   - Interval: METRICS_COLLECTION_INTERVAL, default 5s
#   - What it does: polls service /health counters and DB aggregates, then writes
#     platform/service metrics.
#   - Tables it writes: system_metrics.
#   - External dependencies: HTTP calls to service /health endpoints + DB reads.
#   - Decision: EXTRACT to ops_worker
#   - Reason: periodic aggregation work is independent from request lifecycle.
#
# Task 3: batch_writer
#   - Interval: FLUSH_INTERVAL_MS (default 1000ms) and batch size thresholds.
#   - What it does: buffers and flushes HTTP ingest telemetry writes.
#   - Tables it writes: telemetry.
#   - External dependencies: DB only.
#   - Decision: KEEP in ui_iot
#   - Reason: tightly coupled to HTTP ingest request path shared state.
#
# Task 4: audit_logger
#   - Interval: internal periodic flush loop (configured in shared.audit).
#   - What it does: buffers request-context audit events and flushes asynchronously.
#   - Tables it writes: audit_log.
#   - External dependencies: DB only.
#   - Decision: KEEP in ui_iot
#   - Reason: captures request-context events emitted by ui_iot handlers.

configure_logging("ui_iot")

PG_HOST = os.getenv("PG_HOST", "iot-postgres")
PG_PORT = int(os.getenv("PG_PORT", "5432"))
PG_DB   = os.getenv("PG_DB", "iotcloud")
PG_USER = os.getenv("PG_USER", "iot")
PG_PASS = os.environ["PG_PASS"]
DATABASE_URL = os.getenv("DATABASE_URL")

AUTH_CACHE_TTL = int(os.getenv("AUTH_CACHE_TTL_SECONDS", "60"))
BATCH_SIZE = int(os.getenv("BATCH_SIZE", "500"))
FLUSH_INTERVAL_MS = int(os.getenv("FLUSH_INTERVAL_MS", "1000"))
REQUIRE_TOKEN = os.getenv("REQUIRE_TOKEN", "1") == "1"

UI_REFRESH_SECONDS = int(os.getenv("UI_REFRESH_SECONDS", "5"))

CSRF_COOKIE_NAME = "csrf_token"
CSRF_HEADER_NAME = "X-CSRF-Token"

ALLOWED_ORIGINS = [origin for origin in os.getenv("CORS_ORIGINS", "").split(",") if origin]
if not ALLOWED_ORIGINS:
    if os.getenv("ENV") == "PROD":
        ALLOWED_ORIGINS = []
    else:
        ALLOWED_ORIGINS = [
            "http://localhost:3000",
            "http://localhost:5173",
            "https://localhost:3000",
            "https://localhost:5173",
        ]

app = FastAPI()
app.state.limiter = limiter
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)
app.add_middleware(SlowAPIMiddleware)
app.add_middleware(TraceMiddleware)


class RequestIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())[:8]
        request.state.request_id = request_id
        start = time.monotonic()
        response = await call_next(request)
        duration_ms = int((time.monotonic() - start) * 1000)
        response.headers["X-Request-ID"] = request_id
        logger.info(
            "request",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "status": response.status_code,
                "duration_ms": duration_ms,
            },
        )
        return response


app.add_middleware(RequestIdMiddleware)


@app.middleware("http")
async def deprecate_legacy_integrations_middleware(request: Request, call_next):
    response = await call_next(request)
    if request.url.path.startswith("/customer/integrations") or request.url.path.startswith("/customer/integration-routes"):
        response.headers["X-Deprecated"] = (
            "true; Use /customer/notification-channels instead. "
            "This endpoint will be removed in a future release."
        )
        response.headers["Sunset"] = "2026-06-01"
    return response


app.include_router(devices_router)
app.include_router(alerts_router)
app.include_router(metrics_router)
app.include_router(exports_router)
app.include_router(customer_router)
app.include_router(operator_router)
app.include_router(system_router)
app.include_router(api_v2_router)
app.include_router(api_v2_ws_router)
app.include_router(ingest_router)
app.include_router(users_router)
app.include_router(escalation_router)
app.include_router(notifications_router)
app.include_router(oncall_router)
app.include_router(jobs_router)
app.include_router(roles_router)

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


@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    retry_after = getattr(exc, "retry_after", 60)
    return JSONResponse(
        status_code=429,
        content={"detail": "Rate limit exceeded. Please slow down."},
        headers={"Retry-After": str(retry_after)},
    )

pool: asyncpg.Pool | None = None
background_tasks: list[asyncio.Task] = []

logger = logging.getLogger(__name__)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    trace_id = (
        getattr(request.state, "trace_id", None)
        or getattr(request.state, "request_id", None)
        or ""
    )
    logger.error(
        "unhandled_exception",
        exc_info=exc,
        extra={
            "trace_id": trace_id,
            "method": request.method,
            "path": request.url.path,
            "exception_type": type(exc).__name__,
        },
    )
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error",
            "trace_id": trace_id,
        },
    )


async def _init_db_connection(conn: asyncpg.Connection) -> None:
    # Avoid passing statement_timeout as a startup parameter (PgBouncer rejects it).
    await conn.execute("SET statement_timeout TO 30000")


def _secure_cookies_enabled() -> bool:
    return os.getenv("SECURE_COOKIES", "false").lower() == "true"


CSRF_EXEMPT_PATHS = (
    "/ingest/",
    "/health",
    "/metrics",
    "/webhook/",
    "/.well-known/",
)


@app.middleware("http")
async def csrf_middleware(request: Request, call_next):
    if request.method in ("GET", "HEAD", "OPTIONS"):
        response = await call_next(request)
        if CSRF_COOKIE_NAME not in request.cookies:
            csrf_token = secrets.token_urlsafe(32)
            response.set_cookie(
                CSRF_COOKIE_NAME,
                csrf_token,
                httponly=False,
                secure=_secure_cookies_enabled(),
                samesite="strict",
                path="/",
            )
        return response

    if any(request.url.path.startswith(path) for path in CSRF_EXEMPT_PATHS):
        return await call_next(request)

    cookie_token = request.cookies.get(CSRF_COOKIE_NAME)
    header_token = request.headers.get(CSRF_HEADER_NAME)
    if not cookie_token or not header_token or cookie_token != header_token:
        return JSONResponse(
            status_code=403,
            content={"detail": "CSRF token missing or invalid"},
        )

    return await call_next(request)


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
        if DATABASE_URL:
            pool = await asyncpg.create_pool(
                dsn=DATABASE_URL,
                min_size=2,
                max_size=10,
                command_timeout=30,
                init=_init_db_connection,
            )
        else:
            pool = await asyncpg.create_pool(
                host=PG_HOST, port=PG_PORT, database=PG_DB,
                user=PG_USER, password=PG_PASS,
                min_size=2,
                max_size=10,
                command_timeout=30,
                init=_init_db_connection,
            )
    return pool


@app.on_event("startup")
async def startup():
    await get_pool()

    # Initialize HTTP ingest infrastructure
    app.state.get_pool = get_pool
    app.state.auth_cache = DeviceAuthCache(ttl_seconds=AUTH_CACHE_TTL)
    pool = await get_pool()
    app.state.pool = pool
    app.state.batch_writer = TimescaleBatchWriter(
        pool=pool,
        batch_size=BATCH_SIZE,
        flush_interval_ms=FLUSH_INTERVAL_MS,
    )
    await app.state.batch_writer.start()
    app.state.audit = init_audit_logger(pool, "ui_api")
    await app.state.audit.start()
    app.state.rate_buckets = {}
    app.state.max_payload_bytes = 8192
    app.state.rps = 5.0
    app.state.burst = 20.0
    app.state.require_token = REQUIRE_TOKEN

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

    jwks_uri = os.getenv(
        "KEYCLOAK_JWKS_URI",
        f"{keycloak_internal}/realms/{os.getenv('KEYCLOAK_REALM', 'pulse')}/protocol/openid-connect/certs",
    )
    jwks_ttl = int(os.getenv("JWKS_TTL_SECONDS", "300"))
    try:
        cache = init_jwks_cache(jwks_uri=jwks_uri, ttl_seconds=jwks_ttl)
        await cache.start()
        logger.info("JWKS cache started")
    except Exception:
        # Non-fatal: auth middleware can retry/refresh lazily.
        logger.warning("JWKS cache startup failed", exc_info=True)

    await setup_ws_listener()

@app.on_event("shutdown")
async def shutdown():
    if hasattr(app.state, "batch_writer"):
        await app.state.batch_writer.stop()
    if hasattr(app.state, "audit"):
        await app.state.audit.stop()
    try:
        cache = get_jwks_cache()
        if cache is not None:
            await cache.stop()
    except Exception:
        pass
    try:
        from shared.sampled_logger import get_sampled_logger
        get_sampled_logger().shutdown()
    except Exception:
        pass
    try:
        await shutdown_ws_listener()
    except Exception:
        pass
    for task in background_tasks:
        task.cancel()
    for task in background_tasks:
        try:
            await task
        except asyncio.CancelledError:
            pass

@app.get("/api/v2/health")
async def api_v2_health():
    return {"status": "ok", "service": "pulse-ui", "api_version": "v2"}


@app.get("/healthz")
async def healthz():
    checks: dict[str, str] = {}

    try:
        p = await get_pool()
        async with p.acquire() as conn:
            await conn.fetchval("SELECT 1")
        checks["db"] = "ok"
    except Exception:
        checks["db"] = "unreachable"

    try:
        cache = get_jwks_cache()
        if cache is None:
            checks["keycloak"] = "uninitialized"
        elif cache.is_stale():
            jwks_uri = os.getenv("KEYCLOAK_JWKS_URI", "")
            async with traced_client(timeout=2.0) as client:
                r = await client.get(jwks_uri)
            checks["keycloak"] = "ok" if r.status_code == 200 else f"http_{r.status_code}"
        else:
            checks["keycloak"] = "cached"
    except Exception as exc:
        checks["keycloak"] = f"unreachable: {type(exc).__name__}"

    overall = "ok" if checks.get("db") == "ok" else "degraded"
    return {"status": overall, "checks": checks}


@app.get("/metrics", include_in_schema=False)
async def metrics_endpoint():
    p = await get_pool()
    async with p.acquire() as conn:
        alert_rows = await conn.fetch(
            """
            SELECT tenant_id, COUNT(*) AS cnt
            FROM fleet_alert
            WHERE status IN ('OPEN', 'ACKNOWLEDGED')
            GROUP BY tenant_id
            """
        )
        device_rows = await conn.fetch(
            """
            SELECT tenant_id, status, COUNT(*) AS cnt
            FROM device_state
            GROUP BY tenant_id, status
            """
        )

    for row in alert_rows:
        fleet_active_alerts.labels(tenant_id=row["tenant_id"]).set(row["cnt"])
    for row in device_rows:
        fleet_devices_by_status.labels(
            tenant_id=row["tenant_id"],
            status=row["status"],
        ).set(row["cnt"])

    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

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
        async with traced_client(timeout=10.0) as client:
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
            "organization": payload.get("organization", {}),
            "realm_access": payload.get("realm_access", {}),
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
        async with traced_client(timeout=10.0) as client:
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

    # Log token refresh to audit
    audit = getattr(app.state, "audit", None)
    if audit:
        # Decode minimal info from the new token without full validation
        try:
            from jose import jwt as jwt_mod

            unverified = jwt_mod.get_unverified_claims(access_token)
            audit.auth_token_refresh(
                tenant_id=unverified.get("tenant_id"),
                user_id=unverified.get("sub"),
                email=unverified.get("email"),
                ip_address=request.headers.get("x-forwarded-for", "").split(",")[0].strip()
                or (request.client.host if request.client else "unknown"),
            )
        except Exception:
            pass  # Non-critical; don't break refresh flow

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
        async with traced_client(timeout=5.0) as client:
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


