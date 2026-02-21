# Task 3: WebSocket Ticket Endpoint — Backend

## Context

The frontend currently connects to the WebSocket endpoint with the full JWT in the URL: `?token=<JWT>`. This token appears in server access logs, browser history, CDN logs, and Referer headers.

The fix is a ticket system:
1. The authenticated frontend calls `GET /api/ws-ticket` (requires a valid session/JWT in the header as normal).
2. The server generates a short-lived (30-second TTL), single-use opaque ticket stored in memory.
3. The frontend connects to the WebSocket with `?ticket=<opaque>`.
4. The WebSocket upgrade handler exchanges the ticket for the original user context and deletes it.

This way, no JWT ever appears in a URL.

## Actions

1. Read `services/ui_iot/app.py` to understand the current WebSocket upgrade flow and how `?token=` is validated.

2. Add an in-memory ticket store near the top of `app.py`. Use a dict with TTL cleanup:
   ```python
   import asyncio, secrets, time
   from typing import Optional

   _ws_tickets: dict[str, dict] = {}  # ticket -> {user_context, expires_at}
   _WS_TICKET_TTL = 30  # seconds

   def _cleanup_expired_tickets() -> None:
       now = time.monotonic()
       expired = [k for k, v in _ws_tickets.items() if v["expires_at"] < now]
       for k in expired:
           del _ws_tickets[k]

   def create_ws_ticket(user_context: dict) -> str:
       _cleanup_expired_tickets()
       ticket = secrets.token_urlsafe(32)
       _ws_tickets[ticket] = {
           "user_context": user_context,
           "expires_at": time.monotonic() + _WS_TICKET_TTL,
       }
       return ticket

   def consume_ws_ticket(ticket: str) -> Optional[dict]:
       """Exchange ticket for user context. Single-use: deletes after first use."""
       _cleanup_expired_tickets()
       entry = _ws_tickets.pop(ticket, None)
       if entry is None:
           return None
       if entry["expires_at"] < time.monotonic():
           return None
       return entry["user_context"]
   ```

3. Add a new authenticated REST endpoint `GET /api/ws-ticket`:
   ```python
   @app.get("/api/ws-ticket")
   async def get_ws_ticket(request: Request, ...):
       # Require normal JWT auth (same as all other endpoints)
       # Extract the current user context from the request
       # Create a ticket and return it
       ticket = create_ws_ticket(user_context)
       return {"ticket": ticket}
   ```
   Use the same authentication dependency already used by other protected endpoints.

4. Find the existing WebSocket upgrade handler that currently reads `?token=`. Modify it to also accept `?ticket=`:
   - If `ticket` query param is present: call `consume_ws_ticket(ticket)` to get user context. If None (expired or invalid), reject with 4008 (Policy Violation).
   - If `token` query param is present: keep the existing JWT validation as a fallback for backward compatibility during transition. Add a deprecation log warning.
   - If neither: reject with 4001 (Unauthorized).

5. Do not remove the `?token=` fallback yet — that will be done once the frontend is updated in Task 4.

## Verification

```bash
# Endpoint exists
grep -n 'ws.ticket\|ws_ticket' services/ui_iot/app.py

# Ticket store functions exist
grep -n 'create_ws_ticket\|consume_ws_ticket' services/ui_iot/app.py
```
