# Phase 183: Modal Sizing & Layout Overhaul

## Overview

Fix grossly undersized modals that squish content into tall scrolling columns. After this phase, every modal accommodates its content in one viewport without scrolling wherever possible, using appropriate widths and multi-column layouts.

## Problem

The default `DialogContent` width is `sm:max-w-lg` (512px). At 512px, any form with more than a few fields becomes a tall narrow column requiring vertical scrolling. Specific issues:

1. **AlertRuleDialog** — 5 rule mode buttons overflow 512px, 5-column condition grid is wider than the dialog, 12+ fields stacked vertically with forced scroll
2. **NormalizedMetricDialog** — 4-column mapping table crammed into 512px
3. **CreateUserDialog** — 2-column grid in 448px (sm:max-w-md), each column ~190px
4. **EditTenantDialog** — 20+ fields in single column, always scrolls
5. **CreateCampaignDialog** — Also has raw `<input>` elements (Phase 179 miss)

## Solution

1. **Bump the default** from `sm:max-w-lg` to `sm:max-w-xl` (512→640px) — auto-fixes most medium dialogs
2. **Size tiers** — Assign explicit widths based on content complexity
3. **Multi-column layouts** — Put related fields side-by-side in wider dialogs to reduce height
4. **AlertRuleDialog** — Major restructure: wider, 2-column layout, compact rule mode selector

### Size tier guidelines

| Tier | Class | Width | Use for |
|------|-------|-------|---------|
| S | `sm:max-w-sm` | 384px | Confirmations, 1-field forms |
| M | `sm:max-w-md` | 448px | Simple forms (2-3 fields) |
| L | `sm:max-w-xl` | 640px | **New default.** Standard forms (4-8 fields) |
| XL | `sm:max-w-2xl` | 672px | Forms with tables or many fields |
| 2XL | `sm:max-w-3xl` | 768px | Complex multi-section forms |

## Execution Order

1. `001-default-and-guidelines.md` — Bump default DialogContent width, add explicit sizes to simple dialogs
2. `002-alert-rule-dialog.md` — Major AlertRuleDialog restructure
3. `003-other-dialogs.md` — Fix NormalizedMetricDialog, CreateCampaignDialog, CreateUserDialog, EditTenantDialog
4. `004-update-docs.md` — Documentation updates

## Files Modified Summary

| File | Change |
|------|--------|
| `frontend/src/components/ui/dialog.tsx` | Default `sm:max-w-lg` → `sm:max-w-xl` |
| `frontend/src/features/alerts/AlertRuleDialog.tsx` | `sm:max-w-3xl`, 2-column layout, compact rule mode |
| `frontend/src/features/metrics/NormalizedMetricDialog.tsx` | `sm:max-w-2xl` |
| `frontend/src/features/ota/CreateCampaignDialog.tsx` | `sm:max-w-xl`, fix raw inputs |
| `frontend/src/features/operator/CreateUserDialog.tsx` | `sm:max-w-lg` |
| `frontend/src/features/operator/EditTenantDialog.tsx` | 2-column grid layout |
| `frontend/src/features/alerts/DeleteAlertRuleDialog.tsx` | Explicit `sm:max-w-md` |
| `frontend/src/features/operator/AssignTenantDialog.tsx` | Keep `sm:max-w-md` |
| `frontend/src/features/operator/AssignRoleDialog.tsx` | Keep `sm:max-w-md` |
| `frontend/src/features/users/ChangeRoleDialog.tsx` | Keep `sm:max-w-md` |
| `docs/development/frontend.md` | Document modal sizing guidelines |
| `docs/index.md` | Update feature list |
| `docs/services/ui-iot.md` | Note Phase 183 |

## Verification

```bash
cd frontend && npx tsc --noEmit && npm run build
```

- Default dialog width is 640px (not 512px)
- AlertRuleDialog fits in one viewport without scrolling for simple/anomaly/gap modes
- Multi-condition mode may still scroll with many conditions — that's acceptable
- No modal squishes content into a narrow column
- All existing simple dialogs (confirmations, assign, change role) stay compact
- `npx tsc --noEmit` passes with no errors
