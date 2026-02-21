# Task 6: Normalize Border Radius — One Radius for Cards/Containers

## Rule

| Element | Radius | Tailwind Class |
|---------|--------|----------------|
| Cards, containers, modals, panels | 8px | `rounded-lg` |
| Buttons, inputs, badges, small elements | 6px | `rounded-md` |
| Pills, status dots | 9999px | `rounded-full` |

**Banned:** `rounded-xl` on any element (too round for a data-dense platform). `rounded-sm` (too sharp, inconsistent).

The base Card component was already changed to `rounded-lg` in Task 2. This task sweeps the rest.

## How to Fix

### Step 1: Find all rounded-xl usage

```bash
grep -rn "rounded-xl" frontend/src/ --include="*.tsx" | grep -v node_modules | grep -v card.tsx
```

Change every `rounded-xl` to `rounded-lg`.

### Step 2: Find inconsistent rounded-sm usage on containers

```bash
grep -rn "rounded-sm" frontend/src/ --include="*.tsx" | grep -v node_modules
```

For container/panel elements: change `rounded-sm` to `rounded-lg`.
For small inline elements (badges, tags): `rounded-sm` → `rounded-md`.

### Step 3: Verify rounded-md stays on buttons/inputs

The shadcn Button component already uses `rounded-md` — that's correct, leave it.
Form inputs use `rounded-md` — correct, leave it.

### Step 4: Check for hardcoded border-radius values

```bash
grep -rn "border-radius" frontend/src/ --include="*.tsx" --include="*.css" | grep -v node_modules
```

Replace any hardcoded `border-radius: Xpx` with the appropriate Tailwind class.

## Common Patterns to Fix

```tsx
// Card-like containers
BEFORE: className="rounded-xl border ..."
AFTER:  className="rounded-lg border ..."

// Dialog/modal containers
BEFORE: className="rounded-xl ..."
AFTER:  className="rounded-lg ..."

// Stat/KPI cards
BEFORE: className="rounded-xl bg-card p-4 ..."
AFTER:  className="rounded-lg bg-card p-4 ..."
```

## Verification

```bash
# Should return 0 results
grep -rn "rounded-xl" frontend/src/ --include="*.tsx" | grep -v node_modules | wc -l

cd frontend && npx tsc --noEmit
```
