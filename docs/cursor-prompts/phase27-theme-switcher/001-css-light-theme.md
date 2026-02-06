# Phase 27.1: Add Light Theme CSS Variables

## Task

Refactor `frontend/src/index.css` to support both light and dark themes.

## Current Structure

```css
:root {
  /* Dark theme colors hardcoded here */
  --background: 240 33% 5%;
  --foreground: 0 0% 93%;
  /* ... */
}

.dark {
  /* Only sidebar overrides */
}
```

## New Structure

```css
/* Light theme as default */
:root {
  --background: 0 0% 100%;
  --foreground: 240 10% 10%;
  --card: 0 0% 100%;
  --card-foreground: 240 10% 10%;
  --popover: 0 0% 100%;
  --popover-foreground: 240 10% 10%;
  --primary: 216 89% 50%;
  --primary-foreground: 0 0% 100%;
  --secondary: 240 5% 96%;
  --secondary-foreground: 240 10% 10%;
  --muted: 240 5% 96%;
  --muted-foreground: 240 5% 45%;
  --accent: 240 5% 96%;
  --accent-foreground: 240 10% 10%;
  --destructive: 0 84% 60%;
  --destructive-foreground: 0 0% 100%;
  --border: 240 6% 90%;
  --input: 240 6% 90%;
  --ring: 216 89% 50%;

  /* Sidebar - light */
  --sidebar: 0 0% 98%;
  --sidebar-foreground: 240 10% 10%;
  --sidebar-primary: 216 89% 50%;
  --sidebar-primary-foreground: 0 0% 100%;
  --sidebar-accent: 240 5% 96%;
  --sidebar-accent-foreground: 240 10% 10%;
  --sidebar-border: 240 6% 90%;
  --sidebar-ring: 216 89% 50%;

  /* Charts - light */
  --chart-1: 216 89% 50%;
  --chart-2: 142 71% 45%;
  --chart-3: 38 92% 50%;
  --chart-4: 0 84% 60%;
  --chart-5: 262 83% 58%;
}

/* Dark theme */
.dark {
  --background: 240 33% 5%;
  --foreground: 0 0% 93%;
  --card: 240 20% 8%;
  --card-foreground: 0 0% 93%;
  --popover: 240 20% 8%;
  --popover-foreground: 0 0% 93%;
  --primary: 216 89% 76%;
  --primary-foreground: 240 33% 5%;
  --secondary: 240 10% 15%;
  --secondary-foreground: 0 0% 93%;
  --muted: 240 10% 15%;
  --muted-foreground: 240 5% 55%;
  --accent: 240 10% 15%;
  --accent-foreground: 0 0% 93%;
  --destructive: 4 90% 58%;
  --destructive-foreground: 0 0% 100%;
  --border: 240 10% 20%;
  --input: 240 10% 20%;
  --ring: 216 89% 76%;

  /* Sidebar - dark */
  --sidebar: 240 20% 6%;
  --sidebar-foreground: 0 0% 93%;
  --sidebar-primary: 216 89% 76%;
  --sidebar-primary-foreground: 240 33% 5%;
  --sidebar-accent: 240 10% 12%;
  --sidebar-accent-foreground: 0 0% 93%;
  --sidebar-border: 240 10% 15%;
  --sidebar-ring: 216 89% 76%;

  /* Charts - dark (slightly brighter for visibility) */
  --chart-1: 216 89% 66%;
  --chart-2: 142 71% 55%;
  --chart-3: 38 92% 60%;
  --chart-4: 0 84% 65%;
  --chart-5: 262 83% 68%;
}
```

## Key Changes

1. Move current dark colors into `.dark` class
2. Add light theme colors in `:root`
3. Ensure all variables are defined in both themes
4. Keep chart colors visible in both modes

## Verification

```bash
cd /home/opsconductor/simcloud/frontend && npm run build
```

No CSS errors = success. Visual testing happens after toggle is wired.

## Files

| Action | File |
|--------|------|
| MODIFY | `frontend/src/index.css` |
