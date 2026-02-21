# Task 2: Remove SidebarTrigger from AppHeader

## File
`frontend/src/components/layout/AppHeader.tsx`

## Changes
The `<SidebarTrigger className="-ml-1" />` at the start of the header bar and
the `<Separator orientation="vertical" className="h-5" />` that followed it are
both redundant — the sidebar bottom toggle handles collapse/expand.

### Remove the following from AppHeader:
1. Import: `import { SidebarTrigger } from "@/components/ui/sidebar";`
2. Import: `import { Separator } from "@/components/ui/separator";`
3. JSX element: `<SidebarTrigger className="-ml-1" />`
4. JSX element: `<Separator orientation="vertical" className="h-5" />`

## Verification
Run: `cd frontend && npm run build 2>&1 | tail -5`
Confirm clean build with no unused import warnings turned into errors.
