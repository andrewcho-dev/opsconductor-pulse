# Phase 27: Theme Switcher (Light/Dark Mode)

## Overview

Add a light/dark mode toggle to the UI. Currently the app is dark-only.

## Current State

| Component | State |
|-----------|-------|
| CSS Variables | Dark theme hardcoded in `:root` |
| `.dark` class | Exists but only overrides sidebar vars |
| Light theme | Does not exist |
| Theme toggle | Does not exist |
| ECharts | Only dark theme registered |
| Persistence | None |

## What We'll Build

1. Light theme CSS variables
2. Theme state in Zustand store with localStorage persistence
3. Toggle button in header
4. Dynamic ECharts theme switching
5. System preference detection

## Execute Prompts In Order

1. `001-css-light-theme.md` — Add light theme CSS variables
2. `002-theme-store.md` — Add theme state to Zustand store
3. `003-theme-toggle.md` — Add toggle button to header
4. `004-echarts-light.md` — Add light theme for charts
5. `005-wire-and-test.md` — Wire everything together

## Key Files

| File | Role |
|------|------|
| `frontend/src/index.css` | CSS variables |
| `frontend/src/stores/ui-store.ts` | Theme state |
| `frontend/src/components/layout/AppHeader.tsx` | Toggle button |
| `frontend/src/lib/charts/theme.ts` | ECharts themes |
| `frontend/src/app/providers.tsx` | Apply theme on mount |

## Start Now

Read and execute `001-css-light-theme.md`.
