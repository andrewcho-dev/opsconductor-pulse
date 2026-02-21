# Phase 184: Modal Layout Pass 2 — Logical Grouping & Full-Width Usage

## Problem

Four remaining dialogs are still single-column stacks of fields with no logical grouping, making them unnecessarily tall and poorly organized:

1. **EscalationPolicyModal** — `max-w-4xl` but escalation levels use a cramped `md:grid-cols-12` with 5 columns of content per row. Name + Description stacked vertically.
2. **DeviceEditModal** — No explicit width (640px default). 14 fields in a flat 2-col grid with no section grouping. Location section just separated by a `border-t`.
3. **ChannelModal** — `max-w-2xl` (672px). Name, Type, Enabled all stacked single-column. Channel-specific config sections are reasonable but the header fields waste space.
4. **ScheduleModal** — `max-w-4xl`. Name, Description, Timezone all stacked single-column. Layer config uses `md:grid-cols-4` with unlabeled number inputs.

## Design Principles

- **Use the width.** If a dialog is 1024px wide, pack related short fields side-by-side.
- **Group fields logically.** Use lightweight fieldsets or bordered sections with labels.
- **Label everything.** No unlabeled number inputs.
- **Eliminate vertical waste.** Name + Type + Enabled can share one row. Description doesn't need its own row if it can sit beside another field.

## Execution Order

1. `001-escalation-policy-modal.md` — Restructure escalation policy levels
2. `002-device-edit-modal.md` — Group fields into Hardware / Location fieldsets
3. `003-channel-modal.md` — Pack header fields, improve SMTP layout
4. `004-schedule-modal.md` — Pack header, label layer fields
5. `005-update-docs.md` — Documentation

## Files Modified Summary

| File | Change |
|------|--------|
| `frontend/src/features/escalation/EscalationPolicyModal.tsx` | Widen to `sm:max-w-5xl`, restructure levels as cards, pack header |
| `frontend/src/features/devices/DeviceEditModal.tsx` | Add `sm:max-w-5xl`, group into Hardware/Location fieldsets in 2-col grid |
| `frontend/src/features/notifications/ChannelModal.tsx` | Pack Name+Type+Enabled in one row, widen SMTP section |
| `frontend/src/features/oncall/ScheduleModal.tsx` | Pack Name+Timezone, label all layer fields, 3-col grid |
| `docs/development/frontend.md` | Update modal sizing guidelines |

## Verification

```bash
cd frontend && npx tsc --noEmit && npm run build
```
