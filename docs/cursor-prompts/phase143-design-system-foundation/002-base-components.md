# Task 2: Update Base Components

## Files to Edit

1. `frontend/src/components/ui/card.tsx`
2. `frontend/src/components/ui/table.tsx`
3. `frontend/src/components/ui/data-table.tsx`
4. `frontend/src/components/shared/PageHeader.tsx`

## Changes

### 1. Card component — `frontend/src/components/ui/card.tsx`

The Card base currently uses `gap-6 rounded-xl border py-6 shadow-sm`. Change to:
- `rounded-lg` (8px, industry standard — not the oversized `rounded-xl`)
- Remove `shadow-sm` (borders only, no shadows — matches AWS/Grafana)
- Tighten padding from `py-6` to `py-4` and gap from `gap-6` to `gap-4`

**Card function — change className:**
```
BEFORE: "bg-card text-card-foreground flex flex-col gap-6 rounded-xl border py-6 shadow-sm"
AFTER:  "bg-card text-card-foreground flex flex-col gap-4 rounded-lg border py-4"
```

**CardHeader — change px-6 to px-4, adjust border-b padding:**
```
BEFORE: "... gap-2 px-6 has-data-[slot=card-action]:grid-cols-[1fr_auto] [.border-b]:pb-6"
AFTER:  "... gap-1.5 px-4 has-data-[slot=card-action]:grid-cols-[1fr_auto] [.border-b]:pb-4"
```

**CardTitle — add explicit text size:**
```
BEFORE: "leading-none font-semibold"
AFTER:  "text-sm leading-none font-semibold"
```

**CardContent — change px-6 to px-4:**
```
BEFORE: "px-6"
AFTER:  "px-4"
```

**CardFooter — change px-6 to px-4, adjust border-t padding:**
```
BEFORE: "flex items-center px-6 [.border-t]:pt-6"
AFTER:  "flex items-center px-4 [.border-t]:pt-4"
```

### 2. Table component — `frontend/src/components/ui/table.tsx`

**TableHead — increase row height to 44px, improve padding:**
```
BEFORE: "text-foreground h-10 px-2 text-left align-middle font-medium whitespace-nowrap ..."
AFTER:  "text-foreground h-11 px-3 text-left align-middle font-medium text-xs uppercase tracking-wide text-muted-foreground whitespace-nowrap ..."
```

Note: `h-11` = 44px. Header gets `text-xs uppercase tracking-wide text-muted-foreground` for a clean AWS/Datadog-style header treatment.

**TableCell — improve padding:**
```
BEFORE: "p-2 align-middle whitespace-nowrap ..."
AFTER:  "px-3 py-2.5 align-middle whitespace-nowrap ..."
```

This gives ~44px row height with the text line height.

**TableRow — keep hover behavior, already good.**

### 3. DataTable component — `frontend/src/components/ui/data-table.tsx`

**Change the outer wrapper spacing:**
```
BEFORE: <div className="space-y-4">
AFTER:  <div className="space-y-3">
```

**Change the table container border radius to match cards:**
```
BEFORE: <div className="rounded-md border border-border">
AFTER:  <div className="rounded-lg border border-border overflow-hidden">
```

(Add `overflow-hidden` so the table corners are clipped to the rounded container.)

Also update the loading state container to match:
```
BEFORE: <div className="rounded-md border border-border">
AFTER:  <div className="rounded-lg border border-border overflow-hidden">
```

### 4. PageHeader component — `frontend/src/components/shared/PageHeader.tsx`

**Change the h1 title from text-2xl font-bold to text-xl font-semibold:**
```
BEFORE: <h1 className="text-2xl font-bold">{title}</h1>
AFTER:  <h1 className="text-xl font-semibold">{title}</h1>
```

**Change breadcrumb text-xs to text-sm for legibility:**
```
BEFORE: <nav className="mb-1 flex items-center gap-2 text-xs text-muted-foreground" ...>
AFTER:  <nav className="mb-1 flex items-center gap-1.5 text-sm text-muted-foreground" ...>
```

## Verification

```bash
cd frontend && npx tsc --noEmit
```

Then visually check:
- Cards should have tighter padding, no shadow, `rounded-lg` corners
- Page titles should be `text-xl` (20px), not the oversized `text-2xl` (24px)
- Table headers should have a clean uppercase treatment
- Table rows should be slightly taller (~44px)
