# 001: Critical Security Fixes

## Priority: CRITICAL - Deploy Immediately

## Issues to Fix

### 1. SQL Injection Risk in Dynamic Query Construction

**Files:** `services/ui_iot/routes/customer.py`
**Lines:** 869-876, 1729-1737, 2051-2057, 2304-2312, 3209-3219

**Problem:** Dynamic SQL using f-strings with parameter indices:
```python
# DANGEROUS PATTERN
f"""
UPDATE integrations
SET {", ".join(updates)}
WHERE integration_id = ${param_idx}
"""
```

**Fix:** Use parameterized query builder or ORM pattern:
```python
# SAFE PATTERN - use explicit column mapping
ALLOWED_COLUMNS = {"name", "enabled", "config"}
updates = []
params = []
for key, value in data.items():
    if key in ALLOWED_COLUMNS:
        updates.append(f"{key} = ${len(params) + 1}")
        params.append(value)
# Then validate updates list isn't empty before executing
```

---

### 2. Missing CSRF Protection

**File:** `services/ui_iot/app.py`

**Problem:** No CSRF token validation on state-changing operations.

**Fix:** Add CSRF middleware:
```python
from fastapi import Request, HTTPException
from fastapi.middleware import Middleware
import secrets

CSRF_COOKIE_NAME = "csrf_token"
CSRF_HEADER_NAME = "X-CSRF-Token"

@app.middleware("http")
async def csrf_middleware(request: Request, call_next):
    # Skip for GET, HEAD, OPTIONS (safe methods)
    if request.method in ("GET", "HEAD", "OPTIONS"):
        response = await call_next(request)
        # Set CSRF cookie if not present
        if CSRF_COOKIE_NAME not in request.cookies:
            csrf_token = secrets.token_urlsafe(32)
            response.set_cookie(
                CSRF_COOKIE_NAME,
                csrf_token,
                httponly=False,  # JS needs to read it
                secure=True,
                samesite="strict"
            )
        return response

    # For state-changing methods, validate CSRF token
    cookie_token = request.cookies.get(CSRF_COOKIE_NAME)
    header_token = request.headers.get(CSRF_HEADER_NAME)

    if not cookie_token or not header_token or cookie_token != header_token:
        raise HTTPException(403, "CSRF token missing or invalid")

    return await call_next(request)
```

**Frontend update:** Add CSRF header to all API calls in `frontend/src/services/api/client.ts`:
```typescript
// Get CSRF token from cookie
function getCsrfToken(): string | null {
  const match = document.cookie.match(/csrf_token=([^;]+)/);
  return match ? match[1] : null;
}

// Add to axios interceptor
apiClient.interceptors.request.use((config) => {
  const csrfToken = getCsrfToken();
  if (csrfToken && ['POST', 'PUT', 'PATCH', 'DELETE'].includes(config.method?.toUpperCase() || '')) {
    config.headers['X-CSRF-Token'] = csrfToken;
  }
  return config;
});
```

---

### 3. Audit Log Tenant Bypass

**File:** `services/ui_iot/routes/customer.py`
**Lines:** 3158-3220

**Problem:** Audit endpoint uses `pool.acquire()` instead of `tenant_connection()`, bypassing RLS.

**Fix:** Change to use tenant_connection:
```python
@router.get("/audit")
async def get_audit_log(...):
    tenant_id = get_tenant_id()
    pool = await get_pool()
    # WRONG: async with pool.acquire() as conn:
    # RIGHT:
    async with tenant_connection(pool, tenant_id) as conn:
        # Now RLS is enforced
        rows = await conn.fetch(
            "SELECT * FROM subscription_audit ORDER BY event_timestamp DESC LIMIT $1",
            limit
        )
```

---

### 4. SSRF Protection Disabled in DEV Mode

**File:** `services/delivery_worker/worker.py`
**Lines:** 184-196

**Problem:** SSRF validation only runs when `ENV == "PROD"`.

**Fix:** Always validate, but allow localhost in DEV:
```python
import ipaddress
import socket

PRIVATE_RANGES = [
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("169.254.0.0/16"),
]

def validate_webhook_url(url: str) -> bool:
    """Validate URL is not targeting internal networks."""
    from urllib.parse import urlparse

    parsed = urlparse(url)
    hostname = parsed.hostname

    if not hostname:
        return False

    # Always block internal hostnames
    if hostname in ("localhost", "127.0.0.1", "::1"):
        if os.getenv("ENV") != "DEV":
            return False
        # In DEV, allow localhost but log warning
        logger.warning(f"Allowing localhost webhook in DEV mode: {url}")
        return True

    # Resolve hostname and check IP ranges
    try:
        # Use getaddrinfo for proper resolution
        addrs = socket.getaddrinfo(hostname, None)
        for family, _, _, _, sockaddr in addrs:
            ip = ipaddress.ip_address(sockaddr[0])
            for private_range in PRIVATE_RANGES:
                if ip in private_range:
                    logger.warning(f"Blocked SSRF attempt to private IP: {url} -> {ip}")
                    return False
    except socket.gaierror:
        return False

    return True
```

---

### 5. CORS Allows All Origins

**File:** `services/ui_iot/app.py`
**Lines:** 42, 47

**Problem:** Default CORS allows `*` which is insecure.

**Fix:** Explicitly list allowed origins:
```python
ALLOWED_ORIGINS = os.getenv("CORS_ORIGINS", "").split(",")
if not ALLOWED_ORIGINS or ALLOWED_ORIGINS == [""]:
    # Fallback to same-origin only in production
    if os.getenv("ENV") == "PROD":
        ALLOWED_ORIGINS = []
    else:
        # DEV mode allows localhost
        ALLOWED_ORIGINS = [
            "http://localhost:3000",
            "http://localhost:5173",
            "https://localhost:3000",
            "https://localhost:5173",
        ]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)
```

---

### 6. RuntimeError Instead of HTTPException in Tenant Middleware

**File:** `services/ui_iot/middleware/tenant.py`
**Lines:** 18, 29

**Problem:** Raises RuntimeError which doesn't return proper HTTP response.

**Fix:**
```python
from fastapi import HTTPException

def get_tenant_id() -> str:
    tenant_id = _tenant_id.get()
    if not tenant_id:
        raise HTTPException(401, "Tenant context not established")
    return tenant_id

def get_user() -> dict:
    user = _user.get()
    if not user:
        raise HTTPException(401, "User context not established")
    return user
```

---

### 7. No Rate Limiting on Auth Endpoints

**File:** `services/ui_iot/middleware/auth.py`

**Problem:** Token validation has no rate limiting, vulnerable to brute force.

**Fix:** Add rate limiting middleware for auth:
```python
from collections import defaultdict
from time import time

AUTH_RATE_LIMIT = 100  # requests per window
AUTH_RATE_WINDOW = 60  # seconds

_auth_attempts: dict[str, list[float]] = defaultdict(list)

def check_auth_rate_limit(client_ip: str) -> bool:
    """Check if client IP is within auth rate limit."""
    now = time()
    window_start = now - AUTH_RATE_WINDOW

    # Clean old attempts
    _auth_attempts[client_ip] = [
        t for t in _auth_attempts[client_ip] if t > window_start
    ]

    if len(_auth_attempts[client_ip]) >= AUTH_RATE_LIMIT:
        return False

    _auth_attempts[client_ip].append(now)
    return True
```

---

### 8. Double-Checked Locking Bug in JWKS Cache

**File:** `services/ui_iot/middleware/auth.py`
**Lines:** 42-56

**Problem:** Double-checked locking pattern is incorrect and not thread-safe.

**Fix:** Use proper async locking:
```python
import asyncio

_jwks_lock = asyncio.Lock()
_jwks_cache: dict = {}
_jwks_cache_time: float = 0
JWKS_CACHE_TTL = 3600  # 1 hour

async def get_jwks() -> dict:
    global _jwks_cache, _jwks_cache_time

    now = time()
    if _jwks_cache and (now - _jwks_cache_time) < JWKS_CACHE_TTL:
        return _jwks_cache

    async with _jwks_lock:
        # Check again after acquiring lock
        if _jwks_cache and (now - _jwks_cache_time) < JWKS_CACHE_TTL:
            return _jwks_cache

        async with httpx.AsyncClient() as client:
            response = await client.get(JWKS_URL)
            response.raise_for_status()
            _jwks_cache = response.json()
            _jwks_cache_time = now
            return _jwks_cache
```

---

## Verification

After applying fixes:

```bash
# Test CSRF protection
curl -X POST https://localhost/customer/devices \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"device_id": "test"}'
# Should return 403 CSRF token missing

# Test SSRF protection
# Create webhook with internal URL - should fail
curl -X POST https://localhost/customer/integrations \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"type": "webhook", "url": "http://169.254.169.254/latest/meta-data/"}'
# Should return 400 Invalid URL

# Test CORS
curl -X OPTIONS https://localhost/customer/devices \
  -H "Origin: https://evil.com"
# Should NOT include Access-Control-Allow-Origin: *
```

## Files Changed

- `services/ui_iot/routes/customer.py`
- `services/ui_iot/app.py`
- `services/ui_iot/middleware/tenant.py`
- `services/ui_iot/middleware/auth.py`
- `services/delivery_worker/worker.py`
- `frontend/src/services/api/client.ts`
