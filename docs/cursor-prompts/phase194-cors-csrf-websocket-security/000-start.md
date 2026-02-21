# Phase 194 — CORS, CSRF, and WebSocket Token Security

## Goal

Fix three related HTTP/transport security issues: the CSRF cookie is readable by JavaScript (httponly=False), the CORS configuration defaults to wildcard, and the WebSocket authentication token is placed in the URL query string where it leaks into logs and browser history.

## Current State (problem)

1. **CSRF cookie** (`ui_iot/app.py:491`): `httponly=False` — any XSS can steal the token.
2. **CORS wildcard** (`compose/docker-compose.yml:472`): default is `CORS_ALLOWED_ORIGINS=*` — any origin can make credentialed requests.
3. **WebSocket token in URL** (`frontend/src/services/websocket/manager.ts:39`): `?token=<JWT>` — the token is visible in server access logs, browser history, and proxy logs.

## Target State

- CSRF cookie is always `httponly=True`. The JavaScript layer uses a separate response header to receive the CSRF token value on first load.
- CORS has no wildcard default. If `CORS_ORIGINS` is unset in production the server sends no CORS headers (deny all cross-origin).
- WebSocket connection authenticates via a short-lived ticket: the frontend calls `GET /api/ws-ticket` to get a single-use opaque token (TTL 30s), then connects with `?ticket=<opaque>`. The ticket is exchanged for the real session server-side. No JWT ever appears in a URL.

## Execution Order

| Step | File | What | Depends On |
|------|------|------|------------|
| 1 | `001-csrf-cookie-httponly.md` | Fix CSRF cookie + expose token via header | — |
| 2 | `002-cors-remove-wildcard.md` | Remove CORS wildcard default | — |
| 3 | `003-websocket-ticket-backend.md` | Add ws-ticket endpoint + ticket validation | — |
| 4 | `004-websocket-ticket-frontend.md` | Update frontend WebSocket manager | Step 3 |
| 5 | `005-update-documentation.md` | Update affected docs | Steps 1–4 |

## Verification

```bash
# CSRF: cookie must have HttpOnly flag
curl -c /tmp/cookies.txt -b /tmp/cookies.txt http://localhost:8000/api/auth/session
grep -i httponly /tmp/cookies.txt  # Must show the csrf_token cookie as HttpOnly

# CORS: wildcard must be gone from docker-compose
grep 'CORS_ALLOWED_ORIGINS.*\*' compose/docker-compose.yml
# Must return zero results

# WebSocket URL: no token= in WS connection
grep 'token=' frontend/src/services/websocket/manager.ts
# Must return zero results
```

## Documentation Impact

- `docs/architecture/security.md` — Update CSRF and WebSocket auth sections
- `docs/api/websocket.md` — Document new ticket-based authentication flow
