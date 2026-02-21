# Task 5: Update Documentation

## Context

Phase 197 introduced granular database operator roles, timing-safe admin key comparison, and library-based MQTT password management.

## Files to Update

| File | What Changed |
|------|-------------|
| `docs/architecture/tenant-isolation.md` | Update operator role section: pulse_operator_read (BYPASSRLS, SELECT only) and pulse_operator_write (no BYPASSRLS, limited DML). Remove mention of blanket pulse_operator if present. |
| `docs/operations/security.md` | Document role separation, admin key requirements (min 32 chars), rate limiting on admin endpoints |

## For Each File

1. Read the current content.
2. Update the relevant sections.
3. Update the YAML frontmatter:
   - Set `last-verified` to `2026-02-20`
   - Add `197` to the `phases` array
   - Add relevant source files to `sources`
4. Verify no stale information remains (e.g., references to `pulse_operator` having full write access).
