# Phase 207 — Frontend Accessibility Audit and Remediation

## Goal

Bring the frontend to a baseline WCAG 2.1 AA compliance level. The code review found approximately 39 aria attributes across 176+ components — far too few for a complex enterprise UI. This phase audits the most-used components and fixes the most impactful gaps.

## Current State (problem)

Icon-only buttons have no accessible names, form inputs in some components lack associated labels, modal dialogs may not trap focus, and the alert inbox has no screen-reader-friendly status announcements. Interactive data tables likely have no column header associations.

## Target State

- All icon-only buttons have `aria-label`.
- All form inputs have associated `<label>` elements or `aria-label`.
- Modal dialogs trap focus and announce their title via `aria-labelledby`.
- Alert status changes are announced via `aria-live` regions.
- Data tables have proper `scope` on headers.

## Execution Order

| Step | File | What | Depends On |
|------|------|------|------------|
| 1 | `001-audit-icon-buttons.md` | Find and fix all unlabeled icon buttons | — |
| 2 | `002-audit-form-inputs.md` | Find and fix unlabeled form inputs | — |
| 3 | `003-modal-focus-trap.md` | Verify modal focus trap and aria-labelledby | — |
| 4 | `004-live-regions.md` | Add aria-live regions for alert status changes | — |
| 5 | `005-update-documentation.md` | Update docs | Steps 1–4 |

## Verification

```bash
# Count aria-label usage before and after
grep -rn 'aria-label' frontend/src/ --include="*.tsx" | wc -l
# Should be significantly higher after this phase

# No icon-only buttons without aria-label
grep -rn 'size="icon"' frontend/src/ --include="*.tsx" -l | xargs grep -L 'aria-label'
# Should return zero files
```

## Documentation Impact

- `docs/development/frontend.md` — Add accessibility guidelines: all icon buttons need aria-label, inputs need labels, modals need aria-labelledby
