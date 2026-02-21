# Task 1: Color System & CSS Token Refresh

## Objective

Update the CSS custom properties in `index.css` to shift the primary color from blue to violet/purple, update all related tokens (ring, sidebar, charts), and ensure both light and dark themes are cohesive.

## File to Modify

`frontend/src/index.css`

## Current State

Lines 9-56 define `:root` (light theme) with blue primary:
```css
--primary: 216 89% 50%;        /* Blue */
--ring: 216 89% 50%;            /* Blue */
--sidebar-primary: 216 89% 50%; /* Blue */
--sidebar-ring: 216 89% 50%;    /* Blue */
--chart-1: 216 89% 50%;         /* Blue */
--chart-5: 262 83% 58%;         /* Already violet! */
```

Lines 104-151 define `.dark` with lighter blue:
```css
--primary: 216 89% 76%;
--ring: 216 89% 76%;
--sidebar-primary: 216 89% 76%;
--sidebar-ring: 216 89% 76%;
```

## Changes

### Light Theme (`:root`)

Replace all blue primary values with violet/purple:

```css
/* Primary — shift from blue to violet */
--primary: 262 83% 58%;
--primary-foreground: 0 0% 100%;

/* Ring — match primary */
--ring: 262 83% 58%;

/* Sidebar tokens — match primary */
--sidebar-primary: 262 83% 58%;
--sidebar-primary-foreground: 0 0% 100%;
--sidebar-ring: 262 83% 58%;

/* Sidebar active item — use a subtle violet tint instead of generic gray */
--sidebar-accent: 262 30% 96%;
--sidebar-accent-foreground: 262 40% 30%;

/* Charts — shift chart-1 to violet, keep chart-5 as a complementary color */
--chart-1: 262 83% 58%;
--chart-5: 216 89% 50%;   /* Old blue becomes a chart color */
```

All other light theme tokens remain unchanged (`--background`, `--foreground`, `--card`, `--border`, etc. — these are already clean and neutral).

### Dark Theme (`.dark`)

Replace all blue values with lighter violet for dark mode readability:

```css
--primary: 262 83% 72%;
--primary-foreground: 262 40% 10%;

--ring: 262 83% 72%;

--sidebar-primary: 262 83% 72%;
--sidebar-primary-foreground: 262 40% 10%;
--sidebar-ring: 262 83% 72%;

/* Sidebar active — violet-tinted dark accent */
--sidebar-accent: 262 20% 15%;
--sidebar-accent-foreground: 262 20% 90%;

/* Charts — dark */
--chart-1: 262 83% 68%;
--chart-5: 216 89% 66%;
```

### Background Warmth (Optional but Recommended)

The current light background `220 14% 96%` has a cool blue tint. EMQX uses a warmer, more neutral tone. Consider shifting slightly:

```css
/* Slightly warmer neutral background */
--background: 240 10% 97%;
```

This is subtle — test visually and adjust if needed.

## Important Notes

- The `@theme inline` block (lines 58-102) does NOT need changes — it references the CSS variables, not hardcoded colors.
- The status colors (`--status-online`, `--status-stale`, etc.) remain unchanged — they're semantic and color-independent.
- The grid/drag-drop styles at the bottom of the file are unchanged.
- `--chart-2` (green), `--chart-3` (amber), `--chart-4` (red) remain unchanged — only chart-1 and chart-5 swap.

## Verification

- `npx tsc --noEmit` passes (CSS changes don't affect TypeScript)
- `npm run build` succeeds
- Primary buttons render as violet/purple
- Focus rings are violet
- Sidebar active state uses violet tint
- Dark mode primary is a lighter violet (readable)
- Charts use violet as the primary chart color
- No visual regressions in non-primary-colored elements
