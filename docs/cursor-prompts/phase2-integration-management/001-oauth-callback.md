# Task 001: OAuth Callback with PKCE

> **CURSOR: EXECUTE THIS TASK**
>
> This is an implementation task. Read the instructions below and implement them.
> Modify the files listed in "Files to Create/Modify" section.
> Follow the acceptance criteria to verify your work.
> Commit with the message in the "Commit" section when done.

---

## Context

Phase 1 created `/callback` as a placeholder that doesn't complete the OAuth flow. Keycloak issues an authorization code after login, but the code is never exchanged for tokens. Users cannot actually authenticate.

This task implements the full OAuth 2.0 Authorization Code flow with PKCE (Proof Key for Code Exchange) and CSRF protection via state parameter.

**Read first**:
- `docs/CUSTOMER_PLANE_ARCHITECTURE.md` (Section 1: Unified Authentication Model)
- `services/ui_iot/app.py` (current `/callback` route)
- RFC 7636: Proof Key for Code Exchange (PKCE)
- OAuth 2.0 Security Best Current Practice

**Depends on**: Phase 1 complete

## Task

### 1.1 Create `/login` route to initiate OAuth flow

Add new route `GET /login` in `services/ui_iot/app.py`:

**Generate PKCE parameters**:
- `code_verifier`: 43-128 character random string (use `secrets.token_urlsafe(32)`)
- `code_challenge`: Base64URL(SHA256(code_verifier))
- `code_challenge_method`: `S256`

**Generate state parameter**:
- `state`: Random string (use `secrets.token_urlsafe(32)`)

**Store in secure cookies** (before redirect):
- Cookie `oauth_state`: value=state, HttpOnly=true, SameSite=Lax, Secure=true*, Max-Age=600 (10 min)
- Cookie `oauth_verifier`: value=code_verifier, HttpOnly=true, SameSite=Lax, Secure=true*, Max-Age=600

*`Secure` flag: Set to `true` in production. In development, check env var (e.g., `SECURE_COOKIES=false`) to allow HTTP. Use same pattern as session cookies in section 1.3.

**Build authorization URL**:
```
{KEYCLOAK_URL}/realms/{REALM}/protocol/openid-connect/auth
  ?client_id=pulse-ui
  &response_type=code
  &redirect_uri={callback_url}
  &scope=openid
  &state={state}
  &code_challenge={code_challenge}
  &code_challenge_method=S256
```

**Redirect** to authorization URL.

### 1.2 Modify `/callback` route for token exchange

**Accept parameters**:
- `code` (required): Authorization code from Keycloak
- `state` (required): Must match stored state

**Validate state (CSRF protection)**:
- Read `oauth_state` cookie
- If cookie missing: redirect to `/` with `?error=missing_state`
- If state param missing: redirect to `/` with `?error=missing_state`
- If state != cookie value: redirect to `/` with `?error=state_mismatch`
- Clear `oauth_state` cookie after validation

**Retrieve code_verifier**:
- Read `oauth_verifier` cookie
- If missing: redirect to `/` with `?error=missing_verifier`
- Clear `oauth_verifier` cookie after reading

**Token exchange with PKCE**:
- POST to Keycloak token endpoint: `{KEYCLOAK_URL}/realms/{REALM}/protocol/openid-connect/token`
- Content-Type: `application/x-www-form-urlencoded`
- Body parameters:
  - `grant_type=authorization_code`
  - `client_id=pulse-ui`
  - `code={code}`
  - `redirect_uri={callback_url}`
  - `code_verifier={code_verifier}` ← PKCE proof
- Parse JSON response for `access_token`, `refresh_token`, `expires_in`

### 1.3 Set HTTP-only session cookies

After successful token exchange:

**Session cookie**:
- Name: `pulse_session`
- Value: access_token
- Flags:
  - `HttpOnly=true` (prevent JS access)
  - `Secure=true` (HTTPS only, skip in dev via env var)
  - `SameSite=Lax`
  - `Path=/`
- Max-Age: match `expires_in` from token response

**Refresh cookie**:
- Name: `pulse_refresh`
- Value: refresh_token
- Flags: same as session cookie
- Max-Age: 1800 (30 minutes)

### 1.4 Redirect after success

After setting cookies:
- Decode access_token to get `role` claim
- If role is `operator` or `operator_admin`: redirect to `/operator/dashboard`
- If role is `customer_admin` or `customer_viewer`: redirect to `/customer/dashboard`
- Otherwise: redirect to `/` with `?error=unknown_role`

### 1.5 Error handling

| Condition | Action |
|-----------|--------|
| Missing `code` param | Redirect to `/?error=missing_code` |
| Missing/invalid `state` | Redirect to `/?error=state_mismatch` |
| Missing `oauth_verifier` cookie | Redirect to `/?error=missing_verifier` |
| Token exchange 4xx | Redirect to `/?error=invalid_code` |
| Token exchange 5xx/timeout | Return 503 Service Unavailable |

Log all errors server-side with details for debugging.

### 1.6 Update root route `/`

Modify to check session and redirect appropriately:
- Check for `pulse_session` cookie
- If present: validate token (check expiry)
  - If valid: redirect to appropriate dashboard based on role
  - If expired: redirect to `/login`
- If missing: redirect to `/login`

### 1.7 PKCE helper functions

Create helpers (in app.py or separate module):

```python
import hashlib
import base64
import secrets

def generate_pkce_pair() -> tuple[str, str]:
    """Generate code_verifier and code_challenge for PKCE."""
    verifier = secrets.token_urlsafe(32)  # 43 chars
    challenge = base64.urlsafe_b64encode(
        hashlib.sha256(verifier.encode()).digest()
    ).rstrip(b'=').decode()
    return verifier, challenge

def generate_state() -> str:
    """Generate random state for CSRF protection."""
    return secrets.token_urlsafe(32)
```

## Files to Create/Modify

| Action | Path |
|--------|------|
| MODIFY | `services/ui_iot/app.py` |

**Note**: This task adds the following routes to `app.py`:
- `GET /login` — Initiates OAuth flow with PKCE
- `GET /callback` — Handles OAuth callback (replaces placeholder)
- Modifies `GET /` — Redirects to `/login` or dashboard

## Acceptance Criteria

- [ ] `GET /login` generates PKCE pair and state
- [ ] `GET /login` stores verifier and state in HttpOnly cookies
- [ ] `GET /login` redirects to Keycloak with code_challenge
- [ ] `/callback` validates state against stored cookie
- [ ] `/callback` rejects request if state missing or mismatched
- [ ] `/callback` sends code_verifier in token exchange
- [ ] `/callback` clears oauth_state and oauth_verifier cookies
- [ ] `pulse_session` cookie is set with HttpOnly flag
- [ ] `pulse_refresh` cookie is set
- [ ] User redirected to correct dashboard based on role
- [ ] Invalid state returns error, does not exchange token
- [ ] Subsequent visits to `/` redirect to dashboard (session persists)

**Test flow**:
```
1. Visit http://localhost:8080/
2. Redirected to /login
3. Check cookies: oauth_state and oauth_verifier set
4. Redirected to Keycloak with code_challenge in URL
5. Login as customer1 / test123
6. Redirected back to /callback?code=...&state=...
7. Verify state matches cookie
8. Token exchanged with code_verifier
9. Redirected to /customer/dashboard
10. Check cookies: pulse_session, pulse_refresh exist; oauth_* cleared
11. Refresh page: still on dashboard
```

**Security test**:
```
1. Get valid callback URL with code and state
2. Modify state parameter to different value
3. Submit to /callback
4. Confirm rejection with state_mismatch error
```

## Commit

```
Implement OAuth callback with PKCE and CSRF protection

- GET /login initiates OAuth flow with PKCE (S256)
- Generate and store code_verifier and state in HttpOnly cookies
- Validate state on callback to prevent CSRF
- Exchange code with code_verifier for tokens
- Set session cookies after successful authentication

Part of Phase 2: Customer Integration Management
```
