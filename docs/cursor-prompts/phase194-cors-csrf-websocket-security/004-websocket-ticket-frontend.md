# Task 4: WebSocket Ticket System — Frontend

## Context

After Task 3 adds the `/api/ws-ticket` endpoint, the frontend WebSocket manager must be updated to fetch a ticket before connecting, and update the CSRF token read from the new response header (Task 1).

## Actions

### Part A — WebSocket Manager

1. Read `frontend/src/services/websocket/manager.ts` in full.

2. Before opening the WebSocket, add an async step that fetches a ticket from `/api/ws-ticket`:
   ```typescript
   async function fetchWsTicket(): Promise<string> {
     const res = await fetch("/api/ws-ticket", {
       method: "GET",
       credentials: "include",
       headers: getAuthHeaders(),  // existing auth header utility
     });
     if (!res.ok) throw new Error(`Failed to get WS ticket: ${res.status}`);
     const data = await res.json();
     return data.ticket as string;
   }
   ```

3. In the `connect()` method (or wherever the WebSocket URL is built), replace:
   ```typescript
   // OLD — token in URL
   const url = `${protocol}//${window.location.host}/api/v2/ws?token=${encodeURIComponent(token)}`;
   ```
   With:
   ```typescript
   // NEW — opaque ticket in URL
   const ticket = await fetchWsTicket();
   const url = `${protocol}//${window.location.host}/api/v2/ws?ticket=${encodeURIComponent(ticket)}`;
   ```

4. Remove the `token` parameter from the URL construction entirely.

### Part B — CSRF Token from Header

1. Read `frontend/src/services/api/client.ts` in full.

2. The CSRF token is currently read from `document.cookie`. Change `getCsrfToken()` to also check a module-level in-memory variable that can be populated from the `X-CSRF-Token` response header:

   ```typescript
   let _csrfToken: string | null = null;

   export function storeCsrfToken(token: string): void {
     _csrfToken = token;
   }

   function getCsrfToken(): string | null {
     if (_csrfToken) return _csrfToken;
     // Fallback: read from cookie during transition period
     const match = document.cookie.match(/(?:^|; )csrf_token=([^;]+)/);
     return match ? decodeURIComponent(match[1]) : null;
   }
   ```

3. In the auth/session initialization code (wherever the app calls the session or login endpoint), read the `X-CSRF-Token` response header and call `storeCsrfToken(value)`.

4. Do not remove the cookie fallback yet — it provides backward compatibility during the transition.

## Verification

```bash
grep 'token=' frontend/src/services/websocket/manager.ts
# Must return zero results (no JWT token in URL)

grep 'ws-ticket\|wsTicket\|fetchWsTicket' frontend/src/services/websocket/manager.ts
# Must show ticket fetch logic
```
