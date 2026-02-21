# Phase 44b: Fix Pre-Existing Blockers from Phase 44 Verification

## Two Blockers Found

### Blocker 1 — Operator enum mismatch (API vs DB constraint)

The API validates operators as `GT`, `LT`, `GTE`, `LTE` (symbolic names).
The DB constraint `chk_alert_rules_operator` expects symbols: `>`, `<`, `>=`, `<=`.

These two representations are inconsistent. The evaluator uses the named form internally (`OPERATOR_SYMBOLS` dict maps `GT` → `>`). The DB stores... one of them. These must be reconciled.

### Blocker 2 — Pre-existing TypeScript error in `router.test.tsx`

`npm run build` fails due to a TS error in `frontend/src/app/router.test.tsx`.
This is pre-existing (not introduced by Phase 44).

## Execution Order

| Prompt | Description |
|--------|-------------|
| 001 | Diagnose operator mismatch — read DB constraint + API code |
| 002 | Fix operator mismatch (one source of truth) |
| 003 | Fix TypeScript error in router.test.tsx |
| 004 | Re-run Phase 44 verification gates (both must now pass) |
