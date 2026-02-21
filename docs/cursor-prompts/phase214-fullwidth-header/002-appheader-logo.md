# Task 2: Add Logo as Home Link in AppHeader

## File
`frontend/src/components/layout/AppHeader.tsx`

## Rationale
With the sidebar's branding block removed, the logo needs a new home. Placing it
at the far left of the full-width header matches the EMQX Cloud Console pattern
and makes it a natural home button.

## Changes

### 2a — Ensure isOperator is destructured from useAuth
```tsx
const { isCustomer, isOperator } = useAuth();
```

### 2b — Add logo link as first element inside <header>
After the opening `<header ...>` tag, before the breadcrumb `<nav>`, insert:
```tsx
<Link
  to={isOperator ? "/operator" : "/home"}
  className="flex items-center shrink-0"
  aria-label="Home"
>
  <img
    src="/app/opsconductor_logo_clean_PROPER.svg"
    alt="OpsConductor"
    className="h-7 w-7"
  />
</Link>
<Separator orientation="vertical" className="h-5" />
```

### 2c — Ensure Separator is imported
```tsx
import { Separator } from "@/components/ui/separator";
```

## Verification
Run: `cd frontend && npm run build 2>&1 | tail -5`
