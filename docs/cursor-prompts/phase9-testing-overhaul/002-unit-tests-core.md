# Task 002: Unit Tests — Core (OAuth, Auth, Middleware)

> **CURSOR: EXECUTE THIS TASK**
>
> Read the instructions below and implement them exactly.
> All tests in this task must be UNIT tests — no database, no Keycloak, no network calls.
> Mock all external dependencies. Tests must run in < 5 seconds total.
> RUN THE TESTS in the Test section. Do not proceed if tests fail.

---

## Context

`app.py` is at 23% coverage, `auth.py` is at 82%, and `tenant.py` is at 82%. The OAuth flow, admin endpoints, debug endpoint, and error branches are largely untested. All of these can be unit tested with mocked dependencies.

**Read first**:
- `services/ui_iot/app.py` (login, callback, debug/auth, auth status, auth refresh, admin endpoints)
- `services/ui_iot/middleware/auth.py` (validate_token, get_jwks, fetch_jwks, get_signing_key, JWTBearer)
- `services/ui_iot/middleware/tenant.py` (inject_tenant_context, require_customer, require_customer_admin)

---

## Task

### 2.1 Create `tests/unit/test_oauth_flow.py`

Test the OAuth flow functions in `app.py` without real Keycloak. Use `unittest.mock.patch` to mock `httpx.AsyncClient`.

```python
pytestmark = [pytest.mark.unit, pytest.mark.asyncio]
```

**Test cases for `/login`**:
- `test_login_redirects_to_keycloak` — verify redirect URL contains keycloak hostname, client_id, PKCE challenge, state
- `test_login_sets_state_cookie` — verify `oauth_state` cookie is set with httponly, samesite=lax
- `test_login_sets_verifier_cookie` — verify `oauth_verifier` cookie is set
- `test_login_uses_public_keycloak_url` — mock env vars, verify redirect goes to KEYCLOAK_PUBLIC_URL not KEYCLOAK_INTERNAL_URL

**Test cases for `/callback`**:
- `test_callback_missing_code` — no `code` param → redirect to `/?error=missing_code`
- `test_callback_missing_state_cookie` — no `oauth_state` cookie → redirect to `/?error=missing_state`, verify logger.warning called
- `test_callback_state_mismatch` — state param != cookie → redirect to `/?error=state_mismatch`, verify logger.warning called
- `test_callback_missing_verifier` — no `oauth_verifier` cookie → redirect to `/?error=missing_verifier`, verify logger.warning called
- `test_callback_token_exchange_failure` — mock httpx to return 400 → redirect to `/?error=invalid_code`, verify logger.warning with HTTP status
- `test_callback_token_exchange_server_error` — mock httpx to return 500 → raises HTTPException 503
- `test_callback_token_exchange_network_error` — mock httpx to raise RequestError → raises HTTPException 503
- `test_callback_token_validation_failure` — mock validate_token to raise → redirect to `/?error=invalid_token`, verify logger.warning
- `test_callback_success_customer` — mock everything to succeed, customer role → redirect to `/customer/dashboard`, session cookie set
- `test_callback_success_operator` — mock for operator role → redirect to `/operator/dashboard`
- `test_callback_unknown_role` — mock for unknown role → redirect to `/?error=unknown_role`
- `test_callback_clears_oauth_cookies` — after success, `oauth_state` and `oauth_verifier` cookies deleted

**Test cases for `/logout`**:
- `test_logout_redirects_to_keycloak` — verify redirect includes keycloak logout URL
- `test_logout_clears_session_cookies` — verify `pulse_session` and `pulse_refresh` cookies deleted

**Test cases for `/api/auth/status`**:
- `test_auth_status_no_cookie` — no session → `{"authenticated": false}`
- `test_auth_status_valid_token` — mock validate_token → returns user info
- `test_auth_status_expired_token` — mock validate_token to raise → `{"authenticated": false}`

**Test cases for `/api/auth/refresh`**:
- `test_refresh_no_cookie` — no refresh token → 401
- `test_refresh_success` — mock Keycloak token endpoint → new cookies set
- `test_refresh_keycloak_rejects` — mock 401 response → clears cookies
- `test_refresh_keycloak_down` — mock network error → 503

**Test cases for `/debug/auth`**:
- `test_debug_auth_dev_mode` — MODE=DEV → returns diagnostic JSON
- `test_debug_auth_prod_mode` — MODE=PROD → 404
- `test_debug_auth_hostname_match` — same hostname → status "ok"
- `test_debug_auth_hostname_mismatch` — different hostnames → status "MISCONFIGURED"
- `test_debug_auth_keycloak_unreachable` — mock connection failure → verdict reports unreachable
- `test_debug_auth_issuer_mismatch` — mock wrong issuer → verdict reports mismatch

**Test cases for `root /`**:
- `test_root_no_session` — redirects to /login
- `test_root_customer_session` — mock valid customer token → redirects to /customer/dashboard
- `test_root_operator_session` — mock valid operator token → redirects to /operator/dashboard
- `test_root_invalid_session` — mock expired token → redirects to /login

**Implementation approach**: Use `httpx.ASGITransport` with the FastAPI `app` as the transport. Mock `validate_token` and `httpx.AsyncClient` at the module level using `unittest.mock.patch`.

### 2.2 Create `tests/unit/test_auth_middleware.py`

Test `middleware/auth.py` functions in isolation.

```python
pytestmark = [pytest.mark.unit, pytest.mark.asyncio]
```

**Test cases for `fetch_jwks`**:
- `test_fetch_jwks_success` — mock httpx → returns JWKS
- `test_fetch_jwks_network_error` — mock httpx failure → raises HTTPException 503
- `test_fetch_jwks_uses_internal_url` — verify it calls KEYCLOAK_INTERNAL_URL not public

**Test cases for `get_jwks` (caching)**:
- `test_get_jwks_caches_result` — call twice → only one network call
- `test_get_jwks_refreshes_after_ttl` — mock time.time() past TTL → refetches

**Test cases for `get_signing_key`**:
- `test_get_signing_key_found` — matching kid → returns key
- `test_get_signing_key_not_found` — no matching kid → raises HTTPException 401
- `test_get_signing_key_invalid_header` — malformed token → raises HTTPException 401

**Test cases for `validate_token`**:
- `test_validate_token_expired` — expired JWT → raises HTTPException 401 "Token expired"
- `test_validate_token_wrong_audience` — wrong aud → raises HTTPException 401 "Invalid token claims"
- `test_validate_token_wrong_issuer` — wrong iss → raises HTTPException 401 "Invalid token claims"
- `test_validate_token_bad_signature` — tampered JWT → raises HTTPException 401

**Test cases for `JWTBearer`**:
- `test_jwt_bearer_from_header` — Bearer token in Authorization header → extracts token
- `test_jwt_bearer_from_cookie` — pulse_session cookie → extracts token
- `test_jwt_bearer_header_takes_precedence` — both present → uses header
- `test_jwt_bearer_missing_both` — no header, no cookie → raises HTTPException 401
- `test_jwt_bearer_sets_request_state` — verify `request.state.user` is set

### 2.3 Create `tests/unit/test_tenant_middleware.py`

Test `middleware/tenant.py` functions.

```python
pytestmark = [pytest.mark.unit, pytest.mark.asyncio]
```

**Test cases**:
- `test_inject_tenant_context_extracts_tenant_id` — user with tenant_id → set in request.state
- `test_inject_tenant_context_no_tenant` — user without tenant_id → raises HTTPException 403
- `test_require_customer_admin_passes` — role=customer_admin → no exception
- `test_require_customer_admin_rejects_viewer` — role=customer_viewer → raises HTTPException 403
- `test_require_customer_rejects_operator` — role=operator → raises HTTPException 403

---

## Files to Create

| Action | Path |
|--------|------|
| CREATE | `tests/unit/test_oauth_flow.py` |
| CREATE | `tests/unit/test_auth_middleware.py` |
| CREATE | `tests/unit/test_tenant_middleware.py` |

---

## Test

```bash
# 1. Run only the new unit tests
pytest tests/unit/test_oauth_flow.py tests/unit/test_auth_middleware.py tests/unit/test_tenant_middleware.py -v --tb=short

# 2. Verify they're fast (should be < 5 seconds)
time pytest -m unit -q

# 3. Verify no infrastructure needed (should pass without Keycloak/Postgres running)
# If Keycloak is down, only unit tests should pass — that proves they're true unit tests

# 4. Run full unit suite
pytest -m unit -v

# 5. Check coverage improvement for target files
pytest -m unit --cov=services/ui_iot/app --cov=services/ui_iot/middleware --cov-report=term-missing -q
```

---

## Acceptance Criteria

- [ ] `test_oauth_flow.py` has 25+ test cases covering login, callback, logout, auth status, refresh, debug/auth, root
- [ ] `test_auth_middleware.py` has 12+ test cases covering JWKS, signing key, validate_token, JWTBearer
- [ ] `test_tenant_middleware.py` has 5+ test cases covering tenant injection and role enforcement
- [ ] ALL tests pass with `pytest -m unit`
- [ ] ALL tests run in < 5 seconds total
- [ ] No test requires Keycloak, Postgres, or any network access
- [ ] `app.py` coverage improves from 23% to > 60%
- [ ] `auth.py` coverage improves from 82% to > 90%
- [ ] `tenant.py` coverage improves from 82% to > 90%

---

## Commit

```
Add unit tests for OAuth flow, auth middleware, and tenant middleware

- 40+ unit tests covering login, callback, logout, token refresh,
  debug endpoint, JWKS caching, JWT validation, tenant injection
- All mocked — no infrastructure required, runs in < 5 seconds
- app.py coverage: 23% → 60%+
- auth.py coverage: 82% → 90%+
- tenant.py coverage: 82% → 90%+

Part of Phase 9: Testing Overhaul
```
