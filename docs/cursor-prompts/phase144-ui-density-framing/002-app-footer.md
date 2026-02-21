# Task 2: Create App Footer

## Context

The app has no bottom boundary. Content scrolls into a void. Professional SaaS apps frame their content with header + footer. The footer should be minimal — a thin status bar, not a heavy element.

## Step 1: Create AppFooter component

**Create file:** `frontend/src/components/layout/AppFooter.tsx`

```tsx
import packageJson from "../../../package.json";

export function AppFooter() {
  return (
    <footer className="flex h-8 shrink-0 items-center justify-between border-t border-border bg-card px-4 text-xs text-muted-foreground">
      <span>OpsConductor Pulse v{packageJson.version}</span>
      <span>{new Date().getFullYear()} OpsConductor</span>
    </footer>
  );
}
```

Key details:
- Height: `h-8` (32px) — minimal, just enough for one line
- `shrink-0` — prevents flexbox from collapsing it
- `border-t border-border` — top border mirrors header's bottom border
- `bg-card` — same background as header for visual consistency
- Version string moved from sidebar footer

## Step 2: Integrate into AppShell

**File:** `frontend/src/components/layout/AppShell.tsx`

Add import:
```tsx
import { AppFooter } from "./AppFooter";
```

Add `<AppFooter />` after `</main>` and before `<Toaster>`:
```tsx
<main className="flex-1 overflow-auto p-4">
  <Outlet />
</main>
<AppFooter />
<Toaster richColors position="bottom-right" />
```

## Step 3: Remove version from sidebar footer

**File:** `frontend/src/components/layout/AppSidebar.tsx`

Remove the SidebarFooter entirely (lines 481-485):
```tsx
// DELETE:
<SidebarFooter className="p-4">
  <div className="text-sm text-muted-foreground">
    OpsConductor Pulse v{packageJson.version}
  </div>
</SidebarFooter>
```

Also remove the `packageJson` import at the top of the file:
```tsx
// DELETE:
import packageJson from "../../../package.json";
```

Keep `SidebarFooter` in the imports from `@/components/ui/sidebar` in case it's needed later, but remove its usage.

Actually — to be safe, just empty the footer rather than removing it:
```tsx
<SidebarFooter className="p-2" />
```

## Checkpoint

```bash
cd frontend && npx tsc --noEmit
```
