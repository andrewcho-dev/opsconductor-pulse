# Task 001: Fix Session Timeout — Spontaneous "Missing authorization" Error

> **CURSOR: EXECUTE THIS TASK**
>
> Read the instructions below and implement them exactly.
> Modify only the files listed in "Files to Modify".
> RUN THE TESTS in the Test section. Do not proceed if tests fail.
> IMPORTANT: Do not commit until all tests pass.

---

## Context

**THE PROBLEM**: Users see raw JSON `{"detail":"Missing authorization"}` on screen after leaving a browser tab idle or in the background for a few minutes.

**Root cause chain**:

1. Keycloak access token lifetime is 5 minutes (`accessTokenLifespan: 300` in `compose/keycloak/realm-pulse.json:5`).
2. The `pulse_session` cookie has `max_age=int(expires_in)` (set at `app.py:398` and `app.py:509`). After 5 minutes the browser **silently deletes the cookie** — it's gone, not expired-but-present.
3. `auth.js` schedules a refresh via `setTimeout` at `expiresIn - 60` seconds (~4 min). This is supposed to fire before the cookie/token expire.
4. Browsers **throttle `setTimeout` in background tabs** — Chrome defers timers in background tabs to fire at most once per minute, and can defer further after 5+ minutes of inactivity. The 4-minute timer easily fires at 6-10+ minutes.
5. When the user returns to the tab, the browser sends a request. The `pulse_session` cookie is gone. The middleware at `middleware/auth.py:114` finds no cookie and no Bearer header, raises `HTTPException(status_code=401, detail="Missing authorization")`.
6. FastAPI returns the 401 as raw JSON. There is **no exception handler** to redirect HTML requests to the login page. The browser renders the JSON as-is.
7. The `pulse_refresh` cookie is still valid (30-minute `max_age`). A refresh *would* succeed if attempted, but nothing triggers it.

**Read first**:
- `services/ui_iot/static/js/auth.js` (entire file — 52 lines)
- `services/ui_iot/app.py` (lines 31-36: app creation; lines 392-409: callback set_cookie; lines 460-521: refresh endpoint)
- `compose/keycloak/realm-pulse.json` (line 5: accessTokenLifespan)

---

## Task

### 1.1 Increase Keycloak access token lifetime to 15 minutes

**File**: `compose/keycloak/realm-pulse.json`

**Line 5** — change:

```
"accessTokenLifespan": 300,
```

to:

```
"accessTokenLifespan": 900,
```

This reduces refresh frequency and gives a much larger window for the refresh timer to fire even when throttled.

---

### 1.2 Rewrite `auth.js` with robust token refresh

**File**: `services/ui_iot/static/js/auth.js`

Replace the **entire file** with a new implementation. The new file must have these exact behaviors:

**Globals** (module-level variables):
- `_tokenExpiresAt = 0` — timestamp in ms when the current access token expires
- `_refreshIntervalId = null` — stores the setInterval ID so it can be cleared

**`checkAuthStatus()`** — Keep the existing logic exactly:
- `fetch("/api/auth/status", { credentials: "include" })`
- Return `{ authenticated: false }` on error
- Return the parsed JSON on success

**`refreshToken()`** — Keep the existing logic exactly:
- `fetch("/api/auth/refresh", { method: "POST", credentials: "include" })`
- Return `{ success: false }` on error
- Return the parsed JSON on success

**`redirectToLogin()`** — Keep as-is: `window.location = "/";`

**`scheduleRefresh(expiresIn)`** — New implementation:
- Set `window._tokenExpiresAt = Date.now() + expiresIn * 1000`
- If `_refreshIntervalId` is not null, clear it with `clearInterval`
- Set `_refreshIntervalId = setInterval(maybeRefresh, 30000)` (poll every 30 seconds)

**`maybeRefresh()`** — New function (async):
- If `Date.now() > window._tokenExpiresAt - 90000` (within 90 seconds of expiry or already expired):
  - Call `refreshToken()`
  - If `result.success`: call `scheduleRefresh(result.expires_in || 900)` to reset the expiry tracker
  - If not success: wait 5 seconds (`await new Promise(r => setTimeout(r, 5000))`), retry `refreshToken()` once
    - If retry succeeds: call `scheduleRefresh(result.expires_in || 900)`
    - If retry fails: call `redirectToLogin()`

**Visibility change listener** — New:
- `document.addEventListener("visibilitychange", ...)`
- When `document.visibilityState === "visible"`: call `maybeRefresh()`

**Fetch interceptor** — New:
- Save `window.fetch` to a local variable `const _originalFetch = window.fetch`
- Override `window.fetch` with an async wrapper function that:
  - Calls `_originalFetch` with all the same arguments
  - If `response.status === 401` AND the URL does NOT contain `/api/auth/`:
    - Call `refreshToken()`
    - If refresh succeeds: retry the original request by calling `_originalFetch` again with the same arguments, and return that response
    - If refresh fails: call `redirectToLogin()`
  - Otherwise: return the original response as-is

**`DOMContentLoaded` handler** — Updated:
- Call `checkAuthStatus()`
- If not authenticated: call `redirectToLogin()` and return
- Call `scheduleRefresh(status.expires_in || 900)` (note: default changed from 300 to 900)
- Set up the visibilitychange listener
- Set up the fetch interceptor

**Style requirements**:
- Plain functions, no classes, no modules
- `credentials: "include"` on all fetch calls
- No external dependencies
- Keep the code simple and readable

---

### 1.3 Add 401 exception handler in `app.py`

**File**: `services/ui_iot/app.py`

**(a)** Add a 401 exception handler **after line 36** (after `app.include_router(operator_router)`). This catches 401s and redirects browser page-navigation requests to the login page instead of showing raw JSON:

```python
@app.exception_handler(HTTPException)
async def custom_http_exception_handler(request: Request, exc: HTTPException):
    if exc.status_code == 401:
        accept = request.headers.get("accept", "")
        if "text/html" in accept:
            return RedirectResponse(url="/", status_code=302)
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )
```

Note: `Request`, `HTTPException`, `RedirectResponse`, and `JSONResponse` are already imported at the top of the file. No new imports needed.

---

### 1.4 Add cookie `max_age` buffer in `app.py`

**File**: `services/ui_iot/app.py`

There are **two** places where `pulse_session` cookie is set. Both need a `+ 60` buffer so the cookie outlives the token by 60 seconds, giving the refresh mechanism time to act before the cookie vanishes.

**(b)** In the `/callback` endpoint — **line 398** — change:

```python
        max_age=int(expires_in),
```

to:

```python
        max_age=int(expires_in) + 60,
```

**(c)** In the `/api/auth/refresh` endpoint — **line 509** — change:

```python
        max_age=int(expires_in),
```

to:

```python
        max_age=int(expires_in) + 60,
```

---

## Files to Modify

| Action | Path | What changes |
|--------|------|--------------|
| MODIFY | `compose/keycloak/realm-pulse.json` | `accessTokenLifespan` 300 -> 900 |
| MODIFY | `services/ui_iot/static/js/auth.js` | Full rewrite: visibilitychange, setInterval, retry, fetch interceptor |
| MODIFY | `services/ui_iot/app.py` | (a) Add 401 exception handler; (b)(c) Cookie max_age + 60 in two places |

**Do NOT modify**: `services/ui_iot/middleware/auth.py` — the auth logic there is correct.

---

## Test

### Step 1: Run unit tests

```bash
cd /home/opsconductor/simcloud && python3 -m pytest tests/unit/ -v -x
```

All existing tests must continue to pass. The `auth.js` changes are client-side only and shouldn't break backend tests. The `app.py` exception handler and cookie buffer are additive changes.

### Step 2: Verify the exception handler works

After making the changes, manually verify the logic by reading the code:
- A 401 with `Accept: text/html` should return a 302 redirect to `/`
- A 401 with `Accept: application/json` (or no Accept header) should return JSON `{"detail": "..."}`
- Non-401 HTTPExceptions should pass through unchanged

### Step 3: Verify auth.js has all required pieces

After writing `auth.js`, confirm the file contains:
- [ ] `_tokenExpiresAt` global variable
- [ ] `_refreshIntervalId` global variable
- [ ] `checkAuthStatus()` function with `credentials: "include"`
- [ ] `refreshToken()` function with `credentials: "include"`
- [ ] `redirectToLogin()` function
- [ ] `scheduleRefresh(expiresIn)` using `setInterval` (not `setTimeout`)
- [ ] `maybeRefresh()` with retry-once logic
- [ ] `document.addEventListener("visibilitychange", ...)`
- [ ] Fetch interceptor overriding `window.fetch`
- [ ] `DOMContentLoaded` handler calling all setup functions

### Step 4: Verify cookie max_age buffer

Search for `set_cookie.*pulse_session` in `app.py`. There should be exactly 2 occurrences, both with `max_age=int(expires_in) + 60`.

---

## Acceptance Criteria

- [ ] `accessTokenLifespan` is 900 in realm-pulse.json
- [ ] `auth.js` uses `setInterval` (not `setTimeout`) for refresh polling
- [ ] `auth.js` has `visibilitychange` listener that triggers refresh check
- [ ] `auth.js` has fetch interceptor that catches 401s and retries after refresh
- [ ] `auth.js` has retry-once logic before redirecting to login
- [ ] `app.py` has exception handler that redirects browser 401s to `/`
- [ ] `pulse_session` cookie `max_age` has `+ 60` buffer in both `/callback` and `/api/auth/refresh`
- [ ] All unit tests pass (`python3 -m pytest tests/unit/ -v -x`)

---

## Commit

```
Fix session timeout causing "Missing authorization" JSON error

Background browser tabs throttle setTimeout, causing token refresh to
miss its window. The cookie expires, and 401 is returned as raw JSON.

- Increase Keycloak access token lifetime to 15 minutes
- Rewrite auth.js: setInterval polling, visibilitychange listener,
  fetch 401 interceptor, retry-once before redirect
- Add 401 exception handler to redirect HTML requests to login
- Add 60s buffer to pulse_session cookie max_age

Phase 13: Session Timeout Fix
```
