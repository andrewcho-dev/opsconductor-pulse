# Task 5: Update Documentation

## Context

Phase 194 changed three security-critical behaviors: CSRF cookie is now httpOnly, CORS no longer has a wildcard default, and WebSocket authentication uses a short-lived ticket instead of a JWT in the URL.

## Files to Update

| File | What Changed |
|------|-------------|
| `docs/architecture/security.md` | CSRF: cookie is now httpOnly, token exposed via X-CSRF-Token header. CORS: no wildcard default, explicit header allowlist. |
| `docs/api/websocket.md` | Authentication flow: must call GET /api/ws-ticket first, then connect with ?ticket=. Document ticket TTL (30s, single-use). Remove any mention of ?token= as the primary flow. |

## For Each File

1. Read the current content.
2. Update the relevant sections to reflect the changes above.
3. Update the YAML frontmatter:
   - Set `last-verified` to `2026-02-20`
   - Add `194` to the `phases` array
   - Add `services/ui_iot/app.py` and `frontend/src/services/websocket/manager.ts` to `sources`
4. Verify no stale information remains.
