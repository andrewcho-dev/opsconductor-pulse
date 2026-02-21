# Task 5: Update Documentation

## Context

Phase 199 added runtime WebSocket message validation, moved the MQTT broker URL to env config, removed `as any` casts in the alert rule dialog, and consolidated auth utilities.

## Files to Update

| File | What Changed |
|------|-------------|
| `docs/development/frontend.md` (or equivalent) | Document: (1) all WS messages must be validated with Zod schemas, (2) use `VITE_MQTT_BROKER_URL` for broker config, (3) auth utilities live in `services/api/client.ts` |
| `frontend/.env.example` | Ensure `VITE_MQTT_BROKER_URL` is documented |

## For Each File

1. Read the current content.
2. Update the relevant sections.
3. For docs files: update YAML frontmatter — set `last-verified` to `2026-02-20`, add `199` to `phases` array.
4. Verify no stale information remains.
