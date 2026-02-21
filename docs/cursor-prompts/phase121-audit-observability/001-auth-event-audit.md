# Task 001 -- Auth Event Audit Logging

## Commit Message

```
feat(audit): add auth event logging to audit_log
```

## Objective

Add authentication event convenience methods to `AuditLogger` and integrate them into the JWT auth middleware so every successful and failed authentication attempt is recorded in the `audit_log` table.

## Files to Modify

1. `services/shared/audit.py`
2. `services/ui_iot/middleware/auth.py`

---

## Step 1: Add auth convenience methods to AuditLogger

**File**: `services/shared/audit.py`

Add three new convenience methods to the `AuditLogger` class, after the existing `error()` method (after line 409). Follow the same pattern as the existing convenience methods (e.g., `device_telemetry`, `alert_created`, `config_changed`).

### Method 1: `auth_success`

```python
def auth_success(
    self,
    tenant_id: str,
    user_id: str,
    email: str,
    ip_address: str,
    details: dict | None = None,
):
    self.log(
        "auth.login_success",
        "auth",
        "login",
        f"Successful authentication for {email}",
        tenant_id=tenant_id,
        actor_type="user",
        actor_id=user_id,
        actor_name=email,
        ip_address=ip_address,
        details=details,
    )
```

### Method 2: `auth_failure`

```python
def auth_failure(
    self,
    reason: str,
    ip_address: str,
    details: dict | None = None,
):
    self.log(
        "auth.login_failure",
        "auth",
        "login_failure",
        f"Authentication failed: {reason}",
        severity="warning",
        ip_address=ip_address,
        details={"reason": reason, **(details or {})},
    )
```

### Method 3: `auth_token_refresh`

```python
def auth_token_refresh(
    self,
    tenant_id: str | None = None,
    user_id: str | None = None,
    email: str | None = None,
    ip_address: str | None = None,
    details: dict | None = None,
):
    self.log(
        "auth.token_refresh",
        "auth",
        "refresh",
        f"Token refreshed for {email or 'unknown'}",
        tenant_id=tenant_id,
        actor_type="user",
        actor_id=user_id,
        actor_name=email,
        ip_address=ip_address,
        details=details,
    )
```

---

## Step 2: Integrate auth audit into JWTBearer middleware

**File**: `services/ui_iot/middleware/auth.py`

### 2a: Import `get_audit_logger`

At the top of the file, add to the existing imports:

```python
from shared.audit import get_audit_logger
```

### 2b: Add audit logging to `validate_token`

The `validate_token` function (line 89) raises `HTTPException` on failures. We cannot log audit events here because we do not have access to the `request` object (and therefore no access to `request.app.state.audit` or the client IP). Instead, all audit logging will happen in `JWTBearer.__call__` which has the `request` object.

### 2c: Modify `JWTBearer.__call__` to log auth events

The current `__call__` method (line 132) looks like:

```python
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
```

Replace the entire `__call__` method body with:

```python
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
        audit = get_audit_logger()
        if audit:
            audit.auth_failure(reason="missing_token", ip_address=client_ip)
        raise HTTPException(status_code=401, detail="Missing authorization")

    try:
        payload = await validate_token(token)
    except HTTPException as exc:
        audit = get_audit_logger()
        if audit:
            # Map the detail string to a failure reason
            reason_map = {
                "Token expired": "expired",
                "Invalid token claims": "invalid_claims",
                "Invalid token": "invalid_token",
                "Unknown signing key": "unknown_key",
                "Auth service unavailable": "auth_unavailable",
            }
            reason = reason_map.get(exc.detail, "unknown")
            audit.auth_failure(reason=reason, ip_address=client_ip)
        raise

    request.state.user = payload

    # Log successful auth
    audit = get_audit_logger()
    if audit:
        audit.auth_success(
            tenant_id=payload.get("tenant_id", ""),
            user_id=payload.get("sub", ""),
            email=payload.get("email", "unknown"),
            ip_address=client_ip,
        )

    return HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
```

### Key design decisions

- We use `get_audit_logger()` (the module-level singleton accessor) rather than `request.app.state.audit`. This is because `get_audit_logger()` is already used throughout other services (evaluator, dispatcher, delivery_worker) and works reliably. The `init_audit_logger()` in `app.py` line 318 sets this same singleton.
- We log every successful auth. This is intentional for security audit trails. If volume becomes a concern in the future, a sampling or dedup mechanism can be added.
- The `reason_map` dict maps the `HTTPException.detail` strings to short reason codes. These detail strings are set in `validate_token()` at lines 118-125. If those detail strings change, this map must be updated.
- We guard every audit call with `if audit:` to avoid `AttributeError` if the logger is not yet initialized (e.g., during testing or startup race).

---

## Step 3: Add audit logging for token refresh

**File**: `services/ui_iot/app.py`

In the `auth_refresh` endpoint (line 662), after a successful token refresh (after `validated = await validate_token(access_token)` if present, or after `access_token` is confirmed valid), add:

Find the section around line 693-703 where the refresh succeeds (the `token_payload` has `access_token` and `new_refresh_token`). After this check and before building the response, add:

```python
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
            ip_address=request.headers.get("x-forwarded-for", "").split(",")[0].strip() or (request.client.host if request.client else "unknown"),
        )
    except Exception:
        pass  # Non-critical; don't break refresh flow
```

Place this after the line that checks `if not access_token or not new_refresh_token:` (line 698) and before the line that creates the JSONResponse (line 704).

---

## Verification

1. Start the stack: `docker compose up -d`
2. Trigger a failed auth:
   ```bash
   curl -H "Authorization: Bearer invalid-token" http://localhost:8081/customer/devices
   ```
3. Query audit log:
   ```sql
   SELECT event_type, severity, message, ip_address, details
   FROM audit_log
   WHERE event_type LIKE 'auth.%'
   ORDER BY timestamp DESC
   LIMIT 10;
   ```
4. Expected: a row with `event_type='auth.login_failure'`, `severity='warning'`, and `details` containing `{"reason": "invalid_token"}`.
5. Log in via the UI (valid Keycloak credentials), then query again -- should see `auth.login_success` rows.

## Tests

No new test files needed. Existing auth tests in `tests/unit/test_auth_middleware.py` should continue to pass. If they mock `validate_token`, the audit logger calls will be no-ops because `get_audit_logger()` returns `None` in test environments without initialization.
