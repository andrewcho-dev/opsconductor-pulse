# Task 002: Frontend Auth

> **CURSOR: EXECUTE THIS TASK**
>
> This is an implementation task. Read the instructions below and implement them.
> Modify the files listed in "Files to Create/Modify" section.
> Follow the acceptance criteria to verify your work.
> Commit with the message in the "Commit" section when done.

---

## Context

Tokens are now stored in HTTP-only cookies after OAuth callback. Templates need JavaScript to handle auth state, detect session expiry, and trigger token refresh before expiry.

**Read first**:
- `services/ui_iot/app.py` (callback route from Task 001)
- `services/ui_iot/templates/customer_dashboard.html`
- `services/ui_iot/templates/dashboard.html`

**Depends on**: Task 001

## Task

### 2.1 Create auth status endpoint

Add to `services/ui_iot/app.py`:

**Route**: `GET /api/auth/status`

**Logic**:
- Read `pulse_session` cookie
- If missing: return `{"authenticated": false}`
- Validate token (check expiry, signature)
- If invalid: return `{"authenticated": false}`
- If valid: return:
  ```json
  {
    "authenticated": true,
    "user": {
      "email": "...",
      "role": "...",
      "tenant_id": "..."
    },
    "expires_in": 180
  }
  ```

### 2.2 Create token refresh endpoint

Add to `services/ui_iot/app.py`:

**Route**: `POST /api/auth/refresh`

**Logic**:
- Read `pulse_refresh` cookie
- If missing: return 401
- POST to Keycloak token endpoint with `grant_type=refresh_token`
- If successful: update both cookies with new tokens
- Return: `{"success": true, "expires_in": 300}`
- If refresh fails: clear cookies, return `{"success": false}`

**Cookie flags (MUST match Task 001)**:
When setting updated cookies, use identical flags to Task 001:
- `pulse_session`: HttpOnly=true, Secure=true (prod), SameSite=Lax, Path=/
- `pulse_refresh`: HttpOnly=true, Secure=true (prod), SameSite=Lax, Path=/

This ensures refreshed tokens have the same security properties as initial tokens.

### 2.3 Create logout endpoint update

Modify `/logout` in `services/ui_iot/app.py`:

- Clear `pulse_session` cookie
- Clear `pulse_refresh` cookie
- Redirect to Keycloak logout endpoint

### 2.4 Create auth.js

Create `services/ui_iot/static/js/auth.js`:

**On page load**:
```javascript
// Check auth status
// If not authenticated, redirect to /
// If authenticated, schedule refresh before expiry
```

**Functions to implement**:
- `checkAuthStatus()`: GET /api/auth/status, handle response
- `refreshToken()`: POST /api/auth/refresh
- `scheduleRefresh(expiresIn)`: setTimeout to refresh 60s before expiry
- `redirectToLogin()`: window.location = '/'

**Auto-refresh logic**:
- On load: check status, get expires_in
- Schedule refresh for (expires_in - 60) seconds
- On refresh success: reschedule
- On refresh failure: redirect to login

### 2.5 Update templates

Add to all authenticated templates:

```html
<script src="/static/js/auth.js"></script>
```

**Templates to update**:
- `customer_dashboard.html`
- `customer_device.html`
- `dashboard.html` (operator)
- `device.html` (operator)

### 2.6 Configure static files

Ensure FastAPI serves static files:
```python
from fastapi.staticfiles import StaticFiles
app.mount("/static", StaticFiles(directory="static"), name="static")
```

Create directory if needed: `services/ui_iot/static/js/`

## Files to Create/Modify

| Action | Path |
|--------|------|
| CREATE | `services/ui_iot/static/js/auth.js` |
| MODIFY | `services/ui_iot/app.py` |
| MODIFY | `services/ui_iot/templates/customer_dashboard.html` |
| MODIFY | `services/ui_iot/templates/customer_device.html` |
| MODIFY | `services/ui_iot/templates/dashboard.html` |
| MODIFY | `services/ui_iot/templates/device.html` |

## Acceptance Criteria

- [ ] `GET /api/auth/status` returns auth state from cookie
- [ ] `POST /api/auth/refresh` refreshes tokens and updates cookies
- [ ] `/logout` clears cookies before Keycloak redirect
- [ ] `auth.js` checks status on page load
- [ ] `auth.js` redirects to login if not authenticated
- [ ] Token auto-refreshes before expiry
- [ ] User stays logged in during extended session (> 5 minutes)
- [ ] Static files served correctly at `/static/js/auth.js`

**Test flow**:
```
1. Login as customer1
2. Open browser dev tools, Network tab
3. Wait 4 minutes (token expires at 5 min)
4. Observe /api/auth/refresh call
5. Confirm still logged in after refresh
6. Click logout
7. Confirm cookies cleared
8. Confirm redirected to Keycloak logout then home
```

## Commit

```
Add frontend auth handling with status check and token refresh

- GET /api/auth/status for session validation
- POST /api/auth/refresh for token renewal
- auth.js with auto-refresh before expiry
- Clear cookies on logout

Part of Phase 2: Customer Integration Management
```
