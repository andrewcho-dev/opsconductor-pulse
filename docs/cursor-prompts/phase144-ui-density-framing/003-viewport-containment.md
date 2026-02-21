# Task 3: Viewport Containment

## Context

Currently the outer container uses `min-h-screen` which allows the entire page to overflow the viewport. The body scrolls, not just the content area. This prevents the header and footer from staying pinned and breaks the "framed" appearance.

## Changes

**File:** `frontend/src/components/layout/AppShell.tsx`

Change the outer container:
```
BEFORE: <div className="flex min-h-screen w-full">
AFTER:  <div className="flex h-screen w-full overflow-hidden">
```

Change the content column:
```
BEFORE: <div className="flex flex-1 flex-col">
AFTER:  <div className="flex flex-1 flex-col overflow-hidden">
```

The `<main>` already has `overflow-auto` so it will be the only scrollable area. Header and footer stay pinned.

## What this achieves

```
+--------------------------------------------------+
| Header (h-14, fixed)                              |
+--------------------------------------------------+
| Sidebar |  Main content area                      |
| (fixed) |  (overflow-auto, scrolls independently) |
|         |                                         |
|         |                                         |
+--------------------------------------------------+
| Footer (h-8, fixed)                               |
+--------------------------------------------------+
```

The entire layout is now contained within the viewport. No body scroll. The content area scrolls independently.

## Verify

After this change, visit any page with long content (Devices, Alerts, Audit Log). Confirm:
- Header stays at top
- Footer stays at bottom
- Only the content area scrolls
- Sidebar does not scroll with content

## Checkpoint

```bash
cd frontend && npx tsc --noEmit
```
