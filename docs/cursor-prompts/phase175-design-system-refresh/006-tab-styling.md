# Task 6: Tab Styling — Primary-Colored Underline Variant

## Objective

Update the tab `variant="line"` underline to use the primary (violet) color instead of foreground, and document that hub pages should use `variant="line"` as the standard.

## File to Modify

`frontend/src/components/ui/tabs.tsx`

## Current State

The `TabsTrigger` component (lines 57-74) already supports a `variant="line"` style via the parent `TabsList`. The active underline uses `after:bg-foreground` (line 68):

```tsx
"after:bg-foreground after:absolute after:opacity-0 after:transition-opacity ..."
```

This renders as a dark/light foreground-colored line. EMQX uses a **primary-colored** (purple/violet) underline for active tabs.

## Changes

### Update the underline color

In `TabsTrigger` (line 68), change `after:bg-foreground` to `after:bg-primary`:

**Before:**
```tsx
"after:bg-foreground after:absolute after:opacity-0 after:transition-opacity ..."
```

**After:**
```tsx
"after:bg-primary after:absolute after:opacity-0 after:transition-opacity ..."
```

### Update the active text color for line variant

Currently the active state applies `data-[state=active]:text-foreground` which is correct. But for the line variant, EMQX also uses a slightly bolder active text. The current styling is fine — no change needed here.

### Optional: Increase underline thickness

The current underline is `after:h-0.5` (2px). EMQX uses approximately 2-3px. If you want it slightly thicker:

Change the horizontal tab underline height class in line 68:
- From: `group-data-[orientation=horizontal]/tabs:after:h-0.5`
- To: `group-data-[orientation=horizontal]/tabs:after:h-[2.5px]`

This is subtle — test visually and adjust.

## No Other Tab Changes Needed

The tab component already has:
- `variant="default"` (pill/muted background) — keep for filter toggles
- `variant="line"` (underline) — use for hub page navigation tabs
- Horizontal and vertical orientation support
- Proper focus-visible states

## Usage Convention

Going forward (for Phases 176-177 hub page consolidation), all hub pages with tabbed navigation should use:

```tsx
<Tabs defaultValue="inbox">
  <TabsList variant="line">
    <TabsTrigger value="inbox">Inbox</TabsTrigger>
    <TabsTrigger value="rules">Rules</TabsTrigger>
    <TabsTrigger value="escalation">Escalation</TabsTrigger>
  </TabsList>
  <TabsContent value="inbox">...</TabsContent>
  <TabsContent value="rules">...</TabsContent>
  <TabsContent value="escalation">...</TabsContent>
</Tabs>
```

## Verification

- `npx tsc --noEmit` passes
- Any existing page using `variant="line"` tabs now shows a violet/primary underline instead of dark gray
- Default (pill) variant tabs are unchanged
- Active tab text is foreground colored (readable)
- Underline transitions smoothly on tab change
- Works in both light and dark mode
