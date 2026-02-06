# Phase 27.3: Add Theme Toggle to Header

## Task

Add a theme toggle button to the header, next to the logout button.

## Modify AppHeader.tsx

**File:** `frontend/src/components/layout/AppHeader.tsx`

Add imports:
```typescript
import { Sun, Moon, Monitor } from "lucide-react";
import { useUIStore } from "@/stores/ui-store";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
```

Add theme toggle component inside the header (before logout button):

```typescript
function ThemeToggle() {
  const { theme, setTheme, resolvedTheme } = useUIStore();

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="ghost" size="icon" className="h-8 w-8">
          {resolvedTheme === "dark" ? (
            <Moon className="h-4 w-4" />
          ) : (
            <Sun className="h-4 w-4" />
          )}
          <span className="sr-only">Toggle theme</span>
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end">
        <DropdownMenuItem onClick={() => setTheme("light")}>
          <Sun className="mr-2 h-4 w-4" />
          Light
        </DropdownMenuItem>
        <DropdownMenuItem onClick={() => setTheme("dark")}>
          <Moon className="mr-2 h-4 w-4" />
          Dark
        </DropdownMenuItem>
        <DropdownMenuItem onClick={() => setTheme("system")}>
          <Monitor className="mr-2 h-4 w-4" />
          System
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
```

Add to header JSX (in the right section with other buttons):
```tsx
<div className="flex items-center gap-2">
  <ConnectionStatus />
  <ThemeToggle />  {/* ADD THIS */}
  {/* existing logout button */}
</div>
```

## If DropdownMenu doesn't exist

Create it or use a simple button toggle:

```typescript
function ThemeToggle() {
  const { theme, setTheme, resolvedTheme } = useUIStore();

  const cycleTheme = () => {
    const next = theme === "light" ? "dark" : theme === "dark" ? "system" : "light";
    setTheme(next);
  };

  return (
    <Button variant="ghost" size="icon" className="h-8 w-8" onClick={cycleTheme}>
      {resolvedTheme === "dark" ? (
        <Moon className="h-4 w-4" />
      ) : (
        <Sun className="h-4 w-4" />
      )}
      <span className="sr-only">Toggle theme ({theme})</span>
    </Button>
  );
}
```

## Verification

```bash
cd /home/opsconductor/simcloud/frontend && npm run build
```

## Files

| Action | File |
|--------|------|
| MODIFY | `frontend/src/components/layout/AppHeader.tsx` |
