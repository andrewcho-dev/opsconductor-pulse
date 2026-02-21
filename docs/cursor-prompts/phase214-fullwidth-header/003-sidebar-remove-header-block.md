# Task 3: Remove SidebarHeader Block from AppSidebar

## File
`frontend/src/components/layout/AppSidebar.tsx`

## Rationale
The logo + product name lived in `<SidebarHeader>`. Now that the logo is in the
top header bar, this block is redundant and wastes vertical space in the sidebar.

## Change
Remove the entire `<SidebarHeader>` block:

```tsx
// DELETE THIS ENTIRE BLOCK:
<SidebarHeader className="p-2">
  <Link
    to={isOperator ? "/operator" : "/home"}
    className="flex items-center gap-2 no-underline"
  >
    <img
      src="/app/opsconductor_logo_clean_PROPER.svg"
      alt="OpsConductor Pulse"
      className="h-8 w-8 shrink-0"
    />
    <div className="group-data-[collapsible=icon]:hidden">
      <div className="text-sm font-semibold text-sidebar-foreground">OpsConductor</div>
      <div className="text-sm text-muted-foreground">Pulse</div>
    </div>
  </Link>
</SidebarHeader>
```

Also remove `SidebarHeader` from the import block if it is no longer used anywhere
else in the file.

## Verification
Run: `cd frontend && npm run build 2>&1 | tail -5`
