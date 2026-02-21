# Task 7: Migrate Hardcoded Status Colors to CSS Tokens

## Context

Task 1 added CSS variable tokens for status colors (`--status-online`, `--status-critical`, etc.) and updated the utility classes. Now we need to replace hardcoded Tailwind color classes used for status indicators throughout the codebase.

## Rule

Status indicators must use the token-based classes, NOT hardcoded Tailwind colors:

| Semantic Meaning | Old (hardcoded) | New (token) |
|-----------------|-----------------|-------------|
| Online/healthy | `text-green-500`, `bg-green-500` | `text-status-online`, `bg-status-online` |
| Stale/warning | `text-yellow-500`, `bg-yellow-500`, `text-orange-500` | `text-status-stale`, `bg-status-stale` |
| Offline/inactive | `text-gray-400`, `bg-gray-400` | `text-status-offline`, `bg-status-offline` |
| Critical/error | `text-red-500`, `bg-red-500`, `text-red-600` | `text-status-critical`, `bg-status-critical` |
| Warning severity | `text-orange-500`, `text-amber-500` | `text-status-warning`, `bg-status-warning` |
| Info | `text-blue-400`, `text-blue-500` | `text-status-info`, `bg-status-info` |

## How to Fix

### Step 1: Find status-related color usage

```bash
# Device status colors
grep -rn "text-green-[0-9]\|bg-green-[0-9]" frontend/src/ --include="*.tsx" | grep -i "online\|status\|health"

# Alert severity colors
grep -rn "text-red-[0-9]\|bg-red-[0-9]" frontend/src/ --include="*.tsx" | grep -i "critical\|error\|alert\|severity"

# Warning/stale colors
grep -rn "text-yellow-[0-9]\|bg-yellow-[0-9]\|text-orange-[0-9]\|bg-orange-[0-9]\|text-amber-[0-9]\|bg-amber-[0-9]" frontend/src/ --include="*.tsx" | grep -i "warn\|stale\|severity"
```

### Step 2: Replace in status mapping functions

Look for switch/case or conditional patterns that map status strings to colors. These are the highest-leverage fixes — one change fixes many usages:

```tsx
// TYPICAL PATTERN (device status)
// BEFORE:
const statusColor = status === "ONLINE" ? "text-green-500"
  : status === "STALE" ? "text-yellow-500"
  : "text-gray-400";

// AFTER:
const statusColor = status === "ONLINE" ? "text-status-online"
  : status === "STALE" ? "text-status-stale"
  : "text-status-offline";
```

```tsx
// TYPICAL PATTERN (alert severity)
// BEFORE:
const severityColor = severity === "critical" ? "text-red-500"
  : severity === "warning" ? "text-orange-500"
  : "text-blue-500";

// AFTER:
const severityColor = severity === "critical" ? "text-status-critical"
  : severity === "warning" ? "text-status-warning"
  : "text-status-info";
```

### Step 3: Fix background status dots

Status indicator dots (colored circles next to device names):

```tsx
// BEFORE:
<span className="h-2 w-2 rounded-full bg-green-500" />

// AFTER:
<span className="h-2 w-2 rounded-full bg-status-online" />
```

### Step 4: Handle edge cases

Some colors are used for non-status purposes (chart colors, accent colors, decorative elements). Do NOT change those — only change colors that represent a semantic status.

**Do NOT change:**
- Chart series colors (these use `--chart-1` through `--chart-5`)
- Decorative backgrounds (e.g., gradient accents)
- Primary action colors (already using `--primary`)
- Destructive action colors (already using `--destructive`)

## Important: Register utility classes for Tailwind

The `@utility` blocks in index.css define `status-online`, `severity-critical`, etc. as **text color** utilities. For **background** variants, you need to create matching utilities.

**Add to index.css after the existing utility blocks:**

```css
@utility bg-status-online {
  background-color: hsl(var(--status-online));
}
@utility bg-status-stale {
  background-color: hsl(var(--status-stale));
}
@utility bg-status-offline {
  background-color: hsl(var(--status-offline));
}
@utility bg-status-critical {
  background-color: hsl(var(--status-critical));
}
@utility bg-status-warning {
  background-color: hsl(var(--status-warning));
}
@utility bg-status-info {
  background-color: hsl(var(--status-info));
}
```

Also rename the existing `severity-*` utilities to `text-status-*` for consistency, OR keep both as aliases:

```css
@utility text-status-online {
  color: hsl(var(--status-online));
}
@utility text-status-stale {
  color: hsl(var(--status-stale));
}
@utility text-status-critical {
  color: hsl(var(--status-critical));
}
@utility text-status-warning {
  color: hsl(var(--status-warning));
}
@utility text-status-info {
  color: hsl(var(--status-info));
}
```

## Verification

```bash
# Remaining hardcoded status colors should be minimal (non-status uses only)
grep -rn "text-green-[0-9]\|text-red-[0-9]\|text-yellow-[0-9]\|text-orange-[0-9]" frontend/src/features/ --include="*.tsx" | wc -l

cd frontend && npx tsc --noEmit && npm run build
```
