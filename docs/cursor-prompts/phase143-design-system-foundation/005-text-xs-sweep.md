# Task 5: Replace text-xs Overuse — Enforce 12px Minimum for Body Content

## Rule

`text-xs` (12px) is ONLY allowed on:
- Timestamps and relative dates (e.g., "2 min ago")
- Badge/pill content
- Table footnotes and metadata captions
- Keyboard shortcut hints (kbd elements)
- Chart axis labels (inside chart containers)

`text-xs` is NOT allowed on:
- Card body content
- Table cell content (use `text-sm`)
- Form labels and descriptions
- Button text
- Navigation items
- Any content the user needs to read as primary information

`text-sm` (14px) should be the default body text everywhere.

## How to Fix

### Step 1: Find all text-xs usage

```bash
grep -rn "text-xs" frontend/src/features/ --include="*.tsx" | wc -l
grep -rn "text-xs" frontend/src/components/ --include="*.tsx" | wc -l
```

### Step 2: Evaluate each instance

For each `text-xs` occurrence, determine if it's legitimate (timestamp, badge, chart label) or if it should be `text-sm`.

**Pattern: card/section body content → change to text-sm**
```tsx
// BEFORE — body content shrunk to 12px
<p className="text-xs text-muted-foreground">Device last seen 2 hours ago</p>

// AFTER — body content at 14px
<p className="text-sm text-muted-foreground">Device last seen 2 hours ago</p>
```

**Pattern: table columns → change to text-sm**
```tsx
// BEFORE — table content at 12px
<span className="text-xs">{row.status}</span>

// AFTER — table content at 14px (the Table component already sets text-sm on the table element)
<span className="text-sm">{row.status}</span>
```

Or simply remove `text-xs` from table cells entirely — the `<Table>` base component already applies `text-sm` to the whole table.

**Pattern: form labels/descriptions → change to text-sm**
```tsx
// BEFORE
<label className="text-xs font-medium">Name</label>

// AFTER
<label className="text-sm font-medium">Name</label>
```

**Pattern: KEEP text-xs — legitimate small text**
```tsx
// These are fine as text-xs:
<time className="text-xs text-muted-foreground">2 min ago</time>
<Badge className="text-xs">Active</Badge>
<span className="text-xs text-muted-foreground">Last updated: ...</span>
```

### Step 3: Be thorough but careful

This touches ~99 files in features/ alone. Go through each file methodically. When in doubt, use `text-sm` — 14px is always readable, 12px often isn't at a glance.

**Files to focus on first (highest-traffic pages):**
1. `features/dashboard/` — all widgets and KPI cards
2. `features/devices/` — device list, detail, columns
3. `features/alerts/` — alert list, alert detail
4. `features/operator/` — operator dashboard, NOC views
5. `features/settings/` — profile, organization, billing

### Step 4: Check components/shared/ too

```bash
grep -rn "text-xs" frontend/src/components/shared/ --include="*.tsx"
```

Fix any shared components using `text-xs` for body content.

## Verification

```bash
# Count remaining text-xs — should be significantly lower (target: <100 instances total, down from 434)
grep -rn "text-xs" frontend/src/ --include="*.tsx" | wc -l

cd frontend && npx tsc --noEmit
```
