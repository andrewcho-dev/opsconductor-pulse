# Task 1: Update Design Tokens in index.css

## File

`frontend/src/index.css`

## Changes

### 1. Change light-mode page background from pure white to light gray

This is the single highest-impact change. White cards on light gray background creates natural visual separation without needing borders everywhere.

**In the `:root` block, change:**

```css
/* BEFORE */
--background: 0 0% 100%;

/* AFTER */
--background: 220 14% 96%;
```

### 2. Add an inset/muted background that's slightly lighter than the page

The existing `--muted` is used for many things. Add a subtle inset tone for sections within cards.

**In `:root`, change the sidebar background to be slightly more distinct:**

```css
/* BEFORE */
--sidebar-background: 0 0% 98%;

/* AFTER — match the new page bg so sidebar blends with the page */
--sidebar-background: 220 14% 97%;
```

### 3. Add status color CSS variables

**Add these after the chart variables in `:root`:**

```css
  /* Status semantic colors */
  --status-online: 122 39% 49%;
  --status-stale: 36 100% 50%;
  --status-offline: 0 0% 62%;
  --status-critical: 4 90% 58%;
  --status-warning: 36 100% 50%;
  --status-info: 210 79% 68%;
```

**Add matching dark-mode values in `.dark`:**

```css
  /* Status semantic colors - dark (slightly desaturated for legibility) */
  --status-online: 122 39% 55%;
  --status-stale: 36 80% 55%;
  --status-offline: 0 0% 50%;
  --status-critical: 4 80% 62%;
  --status-warning: 36 80% 55%;
  --status-info: 210 70% 72%;
```

### 4. Register the status colors as theme colors

**In the `@theme inline` block, add:**

```css
  --color-status-online: hsl(var(--status-online));
  --color-status-stale: hsl(var(--status-stale));
  --color-status-offline: hsl(var(--status-offline));
  --color-status-critical: hsl(var(--status-critical));
  --color-status-warning: hsl(var(--status-warning));
  --color-status-info: hsl(var(--status-info));
```

### 5. Replace hardcoded status utility colors with token references

**Replace the existing `@utility` blocks:**

```css
/* BEFORE */
@utility status-online {
  color: #4caf50;
}
@utility status-stale {
  color: #ff9800;
}
@utility severity-critical {
  color: #f44336;
}
@utility severity-warning {
  color: #ff9800;
}
@utility severity-info {
  color: #64b5f6;
}

/* AFTER — use the CSS variable tokens */
@utility status-online {
  color: hsl(var(--status-online));
}
@utility status-stale {
  color: hsl(var(--status-stale));
}
@utility severity-critical {
  color: hsl(var(--status-critical));
}
@utility severity-warning {
  color: hsl(var(--status-warning));
}
@utility severity-info {
  color: hsl(var(--status-info));
}
```

### 6. Do NOT change

- Dark mode `--background: 240 33% 5%` — already good (matches Grafana)
- Dark mode `--card: 240 20% 8%` — already good
- `--radius: 0.5rem` — already correct (8px)
- Chart colors — already fine
- Font family — already correct (system fonts)
- All dark mode values except the status colors added above

## Verification

```bash
cd frontend && npx tsc --noEmit && npm run build
```

Then open in browser — the page background should now be a subtle warm gray instead of pure white. Cards should visually pop against it.
