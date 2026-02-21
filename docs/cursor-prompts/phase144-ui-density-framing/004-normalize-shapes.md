# Task 4: Normalize Shapes — Kill Pill Badges

## Context

The Badge component uses `rounded-full` (pill shape) while buttons use `rounded-md` (6px). When badges appear next to buttons (sidebar, header, modals), the shape clash looks unprofessional.

**Rule:** Rectangular UI elements (badges, chips, tags) use `rounded-md`. Only semantically circular elements (status dots, radio buttons, switches, avatars, progress bars) keep `rounded-full`.

## Step 1: Fix Badge component

**File:** `frontend/src/components/ui/badge.tsx`

In the `badgeVariants` cva base string (line 8), change `rounded-full` to `rounded-md`:

```
BEFORE: "inline-flex items-center justify-center rounded-full border ..."
AFTER:  "inline-flex items-center justify-center rounded-md border ..."
```

This one change fixes ALL badge instances across the app since StatusBadge, SeverityBadge, etc. all use the Badge component.

## Step 2: Fix ConnectionStatus indicator

**File:** `frontend/src/components/shared/ConnectionStatus.tsx`

Change the outer container from pill to rounded rectangle (line 43):

```
BEFORE: "flex items-center gap-1.5 text-xs px-2 py-1 rounded-full border"
AFTER:  "flex items-center gap-1.5 text-xs px-2 py-0.5 rounded-md border"
```

Keep the inner status dot as `rounded-full` (line 51) — that's a circle indicator, not a badge.

## Step 3: Verify no other pill-shaped rectangular elements

Run: `grep -rn "rounded-full" frontend/src/ --include="*.tsx" | grep -v node_modules`

Review each result. The following should KEEP `rounded-full`:
- Status dots (h-2 w-2 elements)
- Switch component (toggle track and thumb)
- Radio group items
- Stepper circles
- UptimeBar / progress bars
- Avatar components (if any)

Everything else should use `rounded-md` or `rounded-lg`.

Fix any remaining rectangular elements that incorrectly use `rounded-full`.

## Checkpoint

```bash
cd frontend && npx tsc --noEmit
```
