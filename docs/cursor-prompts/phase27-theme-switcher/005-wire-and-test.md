# Phase 27.5: Wire Together and Test

## Task

Ensure theme is applied on initial load and test everything works.

## Step 1: Apply theme on app mount

**File:** `frontend/src/App.tsx`

Add initialization at the top of the App component:

```typescript
import { useEffect } from "react";
import { useUIStore } from "@/stores/ui-store";

function App() {
  // Apply theme on mount (handles SSR and initial load)
  useEffect(() => {
    const { theme, setTheme } = useUIStore.getState();
    setTheme(theme); // This applies the theme to DOM
  }, []);

  return (
    // ... existing JSX
  );
}
```

Or, simpler approach - make sure the store applies theme immediately on hydration (already done in 002-theme-store.md via `onRehydrateStorage`).

## Step 2: Handle initial flash

To prevent flash of wrong theme, add this to `frontend/index.html` in the `<head>`:

```html
<script>
  (function() {
    try {
      var stored = localStorage.getItem('pulse-ui-store');
      if (stored) {
        var data = JSON.parse(stored);
        var theme = data.state?.theme || 'system';
        var dark = theme === 'dark' ||
          (theme === 'system' && window.matchMedia('(prefers-color-scheme: dark)').matches);
        if (dark) document.documentElement.classList.add('dark');
      }
    } catch (e) {}
  })();
</script>
```

## Step 3: Build and deploy

```bash
cd /home/opsconductor/simcloud/frontend && npm run build
cp -r dist/* ../services/ui_iot/spa/
cd ../compose && docker compose restart ui
```

## Step 4: Test

1. Open app in browser
2. Click theme toggle in header
3. Verify:
   - Background color changes
   - Sidebar colors change
   - Cards and text change
   - Charts (gauges, pie, line) update colors
   - Preference persists after page refresh
4. Test "System" option responds to OS preference

## Expected Behavior

| Theme | Background | Text | Cards | Charts |
|-------|------------|------|-------|--------|
| Light | White | Dark gray | White with border | Dark lines on light |
| Dark | Near black | Light gray | Dark gray | Light lines on dark |
| System | Follows OS | Follows OS | Follows OS | Follows OS |

## Troubleshooting

**Charts don't update:** Check EChartWrapper is subscribing to `resolvedTheme`

**Flash of wrong theme:** Add the script to index.html

**Toggle not visible:** Check AppHeader imports and JSX

**Colors look wrong:** Check CSS variables in index.css have correct values for both themes

## Files

| Action | File |
|--------|------|
| MODIFY | `frontend/src/App.tsx` (if needed) |
| MODIFY | `frontend/index.html` (anti-flash script) |
