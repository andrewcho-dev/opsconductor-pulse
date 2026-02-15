import os
import time
import logging
from collections import defaultdict

from jose import jwk, jwt
from jose.exceptions import ExpiredSignatureError, JWTClaimsError, JWTError
from fastapi import HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from shared.jwks_cache import get_jwks_cache, init_jwks_cache

logger = logging.getLogger(__name__)

KEYCLOAK_PUBLIC_URL = (
    os.getenv("KEYCLOAK_PUBLIC_URL")
    or os.getenv("KEYCLOAK_URL", "http://localhost:8180")
).rstrip("/")
KEYCLOAK_INTERNAL_URL = (
    os.getenv("KEYCLOAK_INTERNAL_URL") or KEYCLOAK_PUBLIC_URL
).rstrip("/")
KEYCLOAK_REALM = os.getenv("KEYCLOAK_REALM", "pulse")
JWT_AUDIENCE = os.getenv("JWT_AUDIENCE", "pulse-ui")

JWKS_CACHE_TTL = int(os.getenv("JWKS_TTL_SECONDS", "300"))
KEYCLOAK_JWKS_URI = os.getenv(
    "KEYCLOAK_JWKS_URI",
    f"{KEYCLOAK_INTERNAL_URL}/realms/{KEYCLOAK_REALM}/protocol/openid-connect/certs",
)

AUTH_RATE_LIMIT = 100
AUTH_RATE_WINDOW = 60
_auth_attempts: dict[str, list[float]] = defaultdict(list)
def _get_or_init_cache():
    cache = get_jwks_cache()
    if cache is None:
        cache = init_jwks_cache(KEYCLOAK_JWKS_URI, ttl_seconds=JWKS_CACHE_TTL)
    return cache


async def get_jwks() -> dict:
    cache = _get_or_init_cache()
    try:
        keys = await cache.get()
    except Exception:
        logger.exception("Failed to fetch JWKS from cache/provider")
        raise HTTPException(status_code=503, detail="Auth service unavailable")
    return {"keys": keys}


def get_signing_key(token: str, jwks: dict) -> dict:
    try:
        header = jwt.get_unverified_header(token)
    except JWTError:
        logger.exception("Failed to decode token header")
        raise HTTPException(status_code=401, detail="Invalid token")

    kid = header.get("kid")
    if not kid:
        raise HTTPException(status_code=401, detail="Invalid token")

    for key in jwks.get("keys", []):
        if key.get("kid") == kid:
            return key

    raise HTTPException(status_code=401, detail="Unknown signing key")


def _get_client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client:
        return request.client.host
    return "unknown"


def check_auth_rate_limit(client_ip: str) -> bool:
    if os.getenv("PYTEST_CURRENT_TEST"):
        return True
    now = time.time()
    window_start = now - AUTH_RATE_WINDOW
    _auth_attempts[client_ip] = [t for t in _auth_attempts[client_ip] if t > window_start]
    if len(_auth_attempts[client_ip]) >= AUTH_RATE_LIMIT:
        return False
    _auth_attempts[client_ip].append(now)
    return True


async def validate_token(token: str) -> dict:
    jwks = await get_jwks()
    try:
        signing_key = get_signing_key(token, jwks)
    except HTTPException as exc:
        if exc.status_code == 401 and exc.detail == "Unknown signing key":
            cache = _get_or_init_cache()
            try:
                keys = await cache.force_refresh()
                signing_key = get_signing_key(token, {"keys": keys})
            except HTTPException:
                raise
            except Exception:
                logger.exception("Failed to refresh JWKS after key miss")
                raise HTTPException(status_code=503, detail="Auth service unavailable")
        else:
            raise
    issuer = f"{KEYCLOAK_PUBLIC_URL}/realms/{KEYCLOAK_REALM}"

    try:
        key = jwk.construct(signing_key)
        return jwt.decode(
            token,
            key,
            algorithms=["RS256"],
            audience=JWT_AUDIENCE,
            issuer=issuer,
        )
    except ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except JWTClaimsError:
        raise HTTPException(status_code=401, detail="Invalid token claims")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
    except Exception:
        logger.exception("Unexpected error validating token")
        raise HTTPException(status_code=401, detail="Invalid token")


class JWTBearer(HTTPBearer):
    def __init__(self) -> None:
        super().__init__(auto_error=True)

    async def __call__(self, request: Request) -> HTTPAuthorizationCredentials:
        client_ip = _get_client_ip(request)
        if not check_auth_rate_limit(client_ip):
            raise HTTPException(status_code=429, detail="Too many auth attempts")

        token = None
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]
        else:
            token = request.cookies.get("pulse_session")

        if not token:
            raise HTTPException(status_code=401, detail="Missing authorization")

        payload = await validate_token(token)
        request.state.user = payload
        return HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
