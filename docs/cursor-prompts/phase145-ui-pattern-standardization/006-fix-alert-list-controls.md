# Task 6: Fix Alert List Page Controls

## Context

The Alert List page has multiple UI pattern violations:
1. Raw `<button>` HTML instead of `<Button>` component for Refresh and Rules
2. Raw `<button>` elements for tab navigation instead of proper tab components
3. `<Link>` styled as a button for the "Rules" navigation
4. Custom `<details>` element for alert actions instead of DropdownMenu

## Step 1: Fix page header actions

**File:** `frontend/src/features/alerts/AlertListPage.tsx`

Replace the raw HTML buttons in the PageHeader action (lines 173-187):

```tsx
action={
  <div className="flex items-center gap-2">
    <Button
      variant="outline"
      size="sm"
      onClick={() => refetch()}
    >
      <RefreshCw className={`mr-1 h-3.5 w-3.5 ${isFetching ? "animate-spin" : ""}`} />
      Refresh
    </Button>
    <Button variant="outline" size="sm" asChild>
      <Link to="/alert-rules">Rules</Link>
    </Button>
  </div>
}
```

Import `Button` from `@/components/ui/button` if not already imported.

## Step 2: Fix tab buttons

The custom tab buttons (lines 192-212) use raw `<button>` elements with custom styling.

Replace with proper `<Button>` components:

```tsx
<div className="flex flex-wrap gap-2">
  {TABS.map((item) => (
    <Button
      key={item.key}
      variant={tab === item.key ? "default" : "outline"}
      size="sm"
      onClick={() => {
        setTab(item.key);
        setSearch("");
        setSelected(new Set());
        setPageIndex(0);
      }}
    >
      {item.label}
      <span className="ml-2 rounded bg-background/70 px-1.5 py-0.5 text-xs">
        {counts[item.key]}
      </span>
    </Button>
  ))}
</div>
```

## Step 3: Fix bulk action buttons

If there are raw `<button>` elements for bulk actions (Acknowledge Selected, Close Selected), replace with `<Button>` components:

```tsx
<Button variant="outline" size="sm" onClick={() => handleBulk("ack")}>
  Acknowledge Selected ({selected.size})
</Button>
<Button variant="outline" size="sm" onClick={() => handleBulk("close")}>
  Close Selected ({selected.size})
</Button>
```

## Step 4: Fix alert row actions

If alert rows use a custom `<details>` element for the three-dot menu, replace with proper DropdownMenu:

```tsx
<DropdownMenu>
  <DropdownMenuTrigger asChild>
    <Button variant="ghost" size="sm">
      <MoreHorizontal className="h-4 w-4" />
    </Button>
  </DropdownMenuTrigger>
  <DropdownMenuContent align="end">
    <DropdownMenuItem onClick={() => handleAcknowledge(alert.id)}>
      Acknowledge
    </DropdownMenuItem>
    <DropdownMenuItem onClick={() => handleClose(alert.id)}>
      Close
    </DropdownMenuItem>
    <DropdownMenuSeparator />
    <DropdownMenuItem onClick={() => handleSilence(alert.id, 15)}>
      Silence 15m
    </DropdownMenuItem>
    <DropdownMenuItem onClick={() => handleSilence(alert.id, 60)}>
      Silence 1h
    </DropdownMenuItem>
    {alert.device_id && (
      <>
        <DropdownMenuSeparator />
        <DropdownMenuItem asChild>
          <Link to={`/devices/${alert.device_id}`}>View Device</Link>
        </DropdownMenuItem>
      </>
    )}
  </DropdownMenuContent>
</DropdownMenu>
```

Import DropdownMenu components and MoreHorizontal icon.

## Step 5: Sweep for remaining raw HTML buttons

```bash
grep -rn "<button" frontend/src/features/alerts/AlertListPage.tsx
```

Replace any remaining `<button>` with `<Button>`.

## Checkpoint

```bash
cd frontend && npx tsc --noEmit
```
