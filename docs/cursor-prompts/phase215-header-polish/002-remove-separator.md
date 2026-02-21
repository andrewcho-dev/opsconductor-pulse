# Task 2: Remove Vertical Separator Between Logo and Breadcrumbs

## File
`frontend/src/components/layout/AppHeader.tsx`

## Changes

### 2a — Remove the Separator element
Find and delete this line:
```tsx
      <Separator orientation="vertical" className="h-5" />
```

### 2b — Remove the Separator import
Find and delete this import line:
```tsx
import { Separator } from "@/components/ui/separator";
```

## Result
Logo links directly into the breadcrumb nav with just the natural gap-2
spacing of the parent flex container — no divider line.

## Verification
```bash
cd frontend && npm run build 2>&1 | tail -5
```
