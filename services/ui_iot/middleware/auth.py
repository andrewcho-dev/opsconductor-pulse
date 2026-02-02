import asyncio
import os
import time
import logging

import httpx
from jose import jwk, jwt
from jose.exceptions import ExpiredSignatureError, JWTClaimsError, JWTError
from fastapi import HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

logger = logging.getLogger(__name__)

KEYCLOAK_URL = os.getenv("KEYCLOAK_URL", "http://pulse-keycloak:8080").rstrip("/")
KEYCLOAK_REALM = os.getenv("KEYCLOAK_REALM", "pulse")
JWT_AUDIENCE = os.getenv("JWT_AUDIENCE", "pulse-ui")

JWKS_CACHE_TTL = 300
_jwks_cache: dict | None = None
_jwks_cache_time = 0.0
_jwks_lock = asyncio.Lock()


async def fetch_jwks() -> dict:
    jwks_url = f"{KEYCLOAK_URL}/realms/{KEYCLOAK_REALM}/protocol/openid-connect/certs"
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(jwks_url)
            response.raise_for_status()
            return response.json()
    except Exception:
        logger.exception("Failed to fetch JWKS from Keycloak")
        raise HTTPException(status_code=503, detail="Auth service unavailable")


async def get_jwks() -> dict:
    global _jwks_cache, _jwks_cache_time

    now = time.time()
    if _jwks_cache and (now - _jwks_cache_time) < JWKS_CACHE_TTL:
        return _jwks_cache

    async with _jwks_lock:
        now = time.time()
        if _jwks_cache and (now - _jwks_cache_time) < JWKS_CACHE_TTL:
            return _jwks_cache

        _jwks_cache = await fetch_jwks()
        _jwks_cache_time = now
        return _jwks_cache


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


async def validate_token(token: str) -> dict:
    jwks = await get_jwks()
    signing_key = get_signing_key(token, jwks)
    issuer = f"{KEYCLOAK_URL}/realms/{KEYCLOAK_REALM}"

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
