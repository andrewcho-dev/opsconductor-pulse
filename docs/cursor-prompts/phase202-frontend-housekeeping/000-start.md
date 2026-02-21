# Phase 202 — Frontend Housekeeping

## Goal

Clean up accumulated technical debt in the frontend: remove dead code (deprecated `breadcrumbs` prop), eliminate `console.log/warn/error` calls from production code, fix problematic React `useEffect` dependency arrays, and consolidate naive localStorage access.

These are low-severity items individually but together they slow down onboarding, cause performance churn, and make debugging harder in production.

## Current State (problem)

1. **Deprecated `breadcrumbs` prop** (`PageHeader.tsx:12-13`): Still in the TypeScript interface, unused since Phase 175.
2. **`console.*` calls in production**: Multiple files use `console.error`, `console.warn`, `console.log` — these pollute browser devtools for customers and expose internals.
3. **`form` object in `useEffect` dep array** (`AlertRuleDialog.tsx:425`): The `form` object from `useForm()` changes on every render, causing the effect to run excessively.
4. **Naive `localStorage` boolean check** (`AppSidebar.tsx:83-87`): `stored !== "false"` mishandles whitespace and casing edge cases.

## Target State

- `breadcrumbs` prop removed from `PageHeader` and all call sites.
- All `console.*` calls replaced with a structured logger that is a no-op in production.
- `useEffect` dep arrays fixed to not include the `form` object directly.
- `localStorage` access uses `JSON.parse`/`JSON.stringify` for boolean storage.

## Execution Order

| Step | File | What | Depends On |
|------|------|------|------------|
| 1 | `001-remove-deprecated-breadcrumbs.md` | Remove breadcrumbs prop | — |
| 2 | `002-replace-console-calls.md` | Replace console.* with structured logger | — |
| 3 | `003-fix-useeffect-deps.md` | Fix useEffect dependency arrays | — |
| 4 | `004-fix-localstorage-boolean.md` | Fix localStorage boolean serialization | — |
| 5 | `005-update-documentation.md` | Update affected docs | Steps 1–4 |

## Verification

```bash
# No deprecated prop in interface
grep -n 'breadcrumbs.*BreadcrumbItem\|breadcrumbs\?' frontend/src/components/shared/PageHeader.tsx
# Must return zero results

# No direct console calls in production code
grep -rn 'console\.\(log\|warn\|error\|debug\)' frontend/src/ --include="*.tsx" --include="*.ts" | grep -v '.test.\|.spec.\|logger'
# Should return minimal or zero results (only deliberate exceptions)
```

## Documentation Impact

No external docs change. Frontend conventions doc may be updated.
