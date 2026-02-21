# Task 3: Fix Other Undersized Dialogs

## Objective

Fix the remaining dialogs that are undersized or poorly laid out: NormalizedMetricDialog, CreateCampaignDialog, CreateUserDialog, and EditTenantDialog.

---

## 1. NormalizedMetricDialog

**File:** `frontend/src/features/metrics/NormalizedMetricDialog.tsx`

### Problem
Uses default width (was 512px, now 640px after Task 1). The mapping table has 4 columns (Raw Metric, Multiplier, Offset, Actions) that are tight at 640px.

### Fix
Add explicit `sm:max-w-2xl` to DialogContent:

```tsx
// OLD:
<DialogContent>

// NEW:
<DialogContent className="sm:max-w-2xl">
```

Also put Name and Unit side by side:

```tsx
// OLD: Name and Unit stacked vertically
<div className="grid gap-2">
  <Label htmlFor="normalized-name">Name (used in rules)</Label>
  <Input ... />
</div>
<div className="grid gap-2">
  <Label htmlFor="normalized-unit">Display Unit</Label>
  <Input ... />
</div>

// NEW: Name and Unit in a 2-column grid
<div className="grid gap-4 sm:grid-cols-2">
  <div className="grid gap-2">
    <Label htmlFor="normalized-name">Name (used in rules)</Label>
    <Input ... />
  </div>
  <div className="grid gap-2">
    <Label htmlFor="normalized-unit">Display Unit</Label>
    <Input ... />
  </div>
</div>
```

---

## 2. CreateCampaignDialog

**File:** `frontend/src/features/ota/CreateCampaignDialog.tsx`

### Problem
1. Uses `sm:max-w-lg` (512px) — adequate for a wizard but could be slightly wider
2. Has **raw `<input>` elements** on lines 174, 207-208, 219-220 — Phase 179 compliance violation

### Fix

**A. Replace raw `<input>` elements with shadcn `Input`:**

Add the import if not already present:
```tsx
import { Input } from "@/components/ui/input";
```

Replace all raw `<input>` elements:

```tsx
// Step 3, Campaign Name - line 174:
// OLD:
<input
  type="text"
  value={name}
  onChange={(e) => setName(e.target.value)}
  placeholder="e.g., v2.1.0 rollout - production"
  className="mt-1 w-full rounded border border-border bg-background px-3 py-2 text-sm"
/>

// NEW:
<Input
  value={name}
  onChange={(e) => setName(e.target.value)}
  placeholder="e.g., v2.1.0 rollout - production"
  className="mt-1"
/>

// Step 3, Rollout Rate - line 207:
// OLD:
<input
  type="number"
  min={1}
  max={1000}
  value={rolloutRate}
  onChange={(e) => setRolloutRate(Number(e.target.value))}
  className="mt-1 w-full rounded border border-border bg-background px-3 py-2 text-sm"
/>

// NEW:
<Input
  type="number"
  min={1}
  max={1000}
  value={String(rolloutRate)}
  onChange={(e) => setRolloutRate(Number(e.target.value))}
  className="mt-1"
/>

// Step 3, Abort Threshold - line 219:
// OLD:
<input
  type="number"
  min={0}
  max={100}
  value={abortThreshold}
  onChange={(e) => setAbortThreshold(Number(e.target.value))}
  className="mt-1 w-full rounded border border-border bg-background px-3 py-2 text-sm"
/>

// NEW:
<Input
  type="number"
  min={0}
  max={100}
  value={String(abortThreshold)}
  onChange={(e) => setAbortThreshold(Number(e.target.value))}
  className="mt-1"
/>
```

**B. Remove explicit `sm:max-w-lg`** so it picks up the new default (`sm:max-w-xl` = 640px):

```tsx
// OLD:
<DialogContent className="sm:max-w-lg">

// NEW:
<DialogContent>
```

**C. Step 3 layout improvement** — Put Rollout Rate and Abort Threshold side by side:

```tsx
<div className="grid gap-4 sm:grid-cols-2">
  <div>
    <label className="text-sm font-medium">Rollout Rate</label>
    <Input ... className="mt-1" />
  </div>
  <div>
    <label className="text-sm font-medium">Abort Threshold (%)</label>
    <Input ... className="mt-1" />
    <div className="text-sm text-muted-foreground mt-1">
      Auto-abort if &gt;{abortThreshold}% fail.
    </div>
  </div>
</div>
```

---

## 3. CreateUserDialog

**File:** `frontend/src/features/operator/CreateUserDialog.tsx`

### Problem
Uses `sm:max-w-md` (448px) with 2-column grids. Each column is ~190px after padding — labels and inputs are cramped.

### Fix
Upgrade to `sm:max-w-lg` (512px):

```tsx
// OLD:
<DialogContent className="sm:max-w-md">

// NEW:
<DialogContent className="sm:max-w-lg">
```

This gives each column ~220px, which is enough for form labels + inputs to breathe.

---

## 4. EditTenantDialog

**File:** `frontend/src/features/operator/EditTenantDialog.tsx`

### Problem
Has `max-w-2xl max-h-[80vh] overflow-y-auto` with 20+ fields in a single column. Always scrolls.

### Fix

Read the file to understand its structure. Then reorganize fields into 2-column grids where natural pairs exist:

Common patterns for tenant editing:
- **Company info:** Name + Industry side by side
- **Contact:** Contact Name + Contact Email side by side
- **Address:** Address fields in grid (City + State, Country + Postal Code)
- **Limits:** Device Limit + User Limit side by side
- **Settings:** Timezone + Locale side by side

Apply `grid gap-4 sm:grid-cols-2` to pairs of short fields. Keep full-width for: Notes/Description, long text fields, toggles.

Try to eliminate the scroll by fitting the reorganized layout within the viewport. If it still scrolls, keep `max-h-[85vh] overflow-y-auto` as a safety net, but the 2-column layout should significantly reduce height.

---

## Verification

```bash
cd frontend && npx tsc --noEmit
```

- NormalizedMetricDialog opens at 672px with readable mapping table
- CreateCampaignDialog has no raw `<input>` elements, opens at 640px
- CreateCampaignDialog Step 3 shows Rollout Rate + Abort Threshold side by side
- CreateUserDialog opens at 512px with comfortable 2-column grid
- EditTenantDialog uses 2-column layout, reduced scrolling
- All form validation and dirty guards still work
- No TypeScript errors
