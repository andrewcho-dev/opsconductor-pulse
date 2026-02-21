# Task 6: Update Documentation

## Context

Phase 195 enabled MQTT TLS, removed weak EMQX defaults, and added a dev cert generation script.

## Files to Update

| File | What Changed |
|------|-------------|
| `docs/operations/deployment.md` | Add MQTT TLS setup: cert paths, required env vars, port 8883 |
| `docs/development/getting-started.md` | Add step: run `scripts/generate-dev-certs.sh` before `docker compose up` |

## For Each File

1. Read the current content.
2. Update the relevant sections.
3. Update the YAML frontmatter:
   - Set `last-verified` to `2026-02-20`
   - Add `195` to the `phases` array
4. Verify no stale information remains (e.g., references to port 1883 for external connections, or `MQTT_TLS: false` as a valid config).
