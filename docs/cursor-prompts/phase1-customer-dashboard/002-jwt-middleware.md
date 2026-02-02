# Task 002: JWT Validation Middleware

## Context

Keycloak is now running and issuing JWTs. We need middleware to validate these tokens and extract claims for use in route handlers.

**Read first**:
- `docs/CUSTOMER_PLANE_ARCHITECTURE.md` (Section 2: Application-Level Tenant Enforcement)
- `services/ui_iot/app.py` (current FastAPI app structure)

**Depends on**: Task 001 (Keycloak running)

## Task

### 2.1 Modify `services/ui_iot/requirements.txt`

Add these dependencies:
```
python-jose[cryptography]==3.3.0
```

Verify `httpx` is already present (should be from existing code).

### 2.2 Create `services/ui_iot/middleware/__init__.py`

Empty `__init__.py` to make it a package.

### 2.3 Create `services/ui_iot/middleware/auth.py`

Implement JWT validation with JWKS caching.

**Imports needed**:
- `os`, `time`, `asyncio`
- `httpx`
- `jose.jwt`, `jose.jwk`, `jose.exceptions`
- `fastapi` (HTTPException, Request)
- `fastapi.security` (HTTPBearer, HTTPAuthorizationCredentials)

**Environment variables**:
- `KEYCLOAK_URL`: default `http://pulse-keycloak:8080`
- `KEYCLOAK_REALM`: default `pulse`
- `JWT_AUDIENCE`: default `pulse-ui`

**Global state**:
- `_jwks_cache`: dict to store JWKS keys
- `_jwks_cache_time`: timestamp of last fetch
- `JWKS_CACHE_TTL`: 300 seconds (5 minutes)

**Functions to implement**:

1. `async def fetch_jwks() -> dict`:
   - Build URL: `{KEYCLOAK_URL}/realms/{REALM}/protocol/openid-connect/certs`
   - Use httpx.AsyncClient to GET the JWKS
   - Timeout: 10 seconds
   - Return the JSON response
   - On error: log and raise HTTPException(503, "Auth service unavailable")

2. `async def get_jwks() -> dict`:
   - Check if cache is valid (exists and not expired)
   - If valid, return cached JWKS
   - Otherwise, fetch new JWKS, update cache and timestamp
   - Return JWKS

3. `def get_signing_key(token: str, jwks: dict) -> dict`:
   - Decode token header (unverified) to get `kid`
   - Search JWKS keys for matching `kid`
   - If not found: raise HTTPException(401, "Unknown signing key")
   - Return the key dict

4. `async def validate_token(token: str) -> dict`:
   - Get JWKS
   - Get signing key for token
   - Decode and verify token using `jose.jwt.decode()`:
     - Key: the signing key
     - Algorithms: `["RS256"]`
     - Audience: `JWT_AUDIENCE`
     - Issuer: `{KEYCLOAK_URL}/realms/{REALM}`
   - On `ExpiredSignatureError`: raise HTTPException(401, "Token expired")
   - On `JWTClaimsError`: raise HTTPException(401, "Invalid token claims")
   - On `JWTError`: raise HTTPException(401, "Invalid token")
   - Return decoded payload

5. `class JWTBearer(HTTPBearer)`:
   - Constructor: call `super().__init__(auto_error=True)`
   - Override `async def __call__(self, request: Request)`:
     - Call `credentials = await super().__call__(request)`
     - If no credentials: raise HTTPException(401, "Missing authorization")
     - Call `payload = await validate_token(credentials.credentials)`
     - Store payload in `request.state.user = payload`
     - Return credentials

**Error handling**:
- All auth errors must return 401 Unauthorized
- Never leak internal error details to client
- Log errors server-side for debugging

## Files to Create/Modify

| Action | Path |
|--------|------|
| MODIFY | `services/ui_iot/requirements.txt` |
| CREATE | `services/ui_iot/middleware/__init__.py` |
| CREATE | `services/ui_iot/middleware/auth.py` |

## Acceptance Criteria

- [ ] `python -c "from middleware.auth import JWTBearer, validate_token"` works
- [ ] Valid token from Keycloak passes validation
- [ ] Expired token returns 401
- [ ] Token with wrong audience returns 401
- [ ] Token with invalid signature returns 401
- [ ] Missing Authorization header returns 401
- [ ] JWKS is cached (second call doesn't hit Keycloak)

**Test with**:
```python
# Get a token
token = "..." # from curl command in Task 001

# Test validation
import asyncio
from middleware.auth import validate_token
payload = asyncio.run(validate_token(token))
print(payload)  # Should show tenant_id, role, etc.
```

## Commit

```
Add JWT middleware for Keycloak token validation

- JWKS fetching with 5-minute cache
- RS256 signature verification
- Audience and issuer validation
- JWTBearer dependency for FastAPI routes
- Stores decoded payload in request.state.user

Part of Phase 1: Customer Read-Only Dashboard
```
