# 135-001: Customer-Facing Table Pages (Batch 1 — High Traffic)

## Task
Convert 4 high-traffic customer pages from raw `<table>` to `DataTable`.

## Reference Pattern (UsersPage — server-side pagination)
```typescript
import { DataTable } from "@/components/ui/data-table";
import { type ColumnDef, type PaginationState } from "@tanstack/react-table";

const columns: ColumnDef<MyType>[] = [
  { accessorKey: "name", header: "Name" },
  { id: "actions", enableSorting: false, cell: ({ row }) => (/* buttons */) },
];

<DataTable
  columns={columns}
  data={items}
  totalCount={total}
  pagination={{ pageIndex: page - 1, pageSize: limit }}
  onPaginationChange={(updater) => {
    const next = typeof updater === "function"
      ? updater({ pageIndex: page - 1, pageSize: limit })
      : (updater as PaginationState);
    setPage(next.pageIndex + 1);
  }}
  isLoading={isLoading}
  emptyState={<div className="text-center py-8 text-muted-foreground">No items found.</div>}
/>
```

## Reference Pattern (AlertRulesPage — client-side, no pagination)
```typescript
<DataTable
  columns={columns}
  data={rows}
  isLoading={isLoading}
  emptyState={<EmptyState title="No items" description="Create one to get started." icon={<Icon />} />}
/>
```

---

## 1. NotificationChannelsPage
**File**: `frontend/src/features/notifications/NotificationChannelsPage.tsx`

Replace the raw `<table>` with DataTable. Define columns:
- `name` (sortable) — channel name, bold
- `channel_type` (sortable) — Badge showing type (slack, email, webhook, etc.)
- `is_enabled` (sortable) — Badge variant: `default` for enabled, `secondary` for disabled
- `created_at` (sortable) — formatted date
- `actions` (non-sortable) — preserve existing Edit and Delete buttons, use DropdownMenu pattern:
  ```typescript
  {
    id: "actions",
    enableSorting: false,
    cell: ({ row }) => (
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button variant="ghost" size="icon"><MoreHorizontal className="h-4 w-4" /></Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end">
          <DropdownMenuItem onClick={() => onEdit(row.original)}>Edit</DropdownMenuItem>
          <DropdownMenuItem className="text-destructive" onClick={() => onDelete(row.original)}>Delete</DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>
    ),
  }
  ```

**Empty state**: "No notification channels configured. Add a channel to start receiving alerts."
**Loading**: `isLoading={isLoading}` from the query hook.
**Pagination**: Client-side (small dataset), no pagination props needed.

**Imports to add**:
```typescript
import { DataTable } from "@/components/ui/data-table";
import { type ColumnDef } from "@tanstack/react-table";
import { DropdownMenu, DropdownMenuTrigger, DropdownMenuContent, DropdownMenuItem } from "@/components/ui/dropdown-menu";
import { MoreHorizontal } from "lucide-react";
```

**Imports to remove**: Remove `Table, TableHeader, TableBody, TableCell, TableHead, TableRow` from `@/components/ui/table` if no longer used.

---

## 2. EscalationPoliciesPage
**File**: `frontend/src/features/escalation/EscalationPoliciesPage.tsx`

Currently has a raw `<table>` with manual loading (`Loading policies...`) and empty state (`No escalation policies configured.`).

Define columns:
- `name` (sortable) — policy name (bold) with description as `text-xs text-muted-foreground` below
- `is_default` (sortable) — Badge "Default" or empty
- `levels_count` / `# Levels` (sortable) — number of escalation levels
- `created_at` (sortable) — formatted date
- `actions` (non-sortable) — preserve Edit and Delete buttons

Remove all manual loading/empty state `<tr>` elements. Let DataTable handle them via `isLoading` and `emptyState` props.

**Empty state**: "No escalation policies configured. Create a policy to define alert escalation behavior."

---

## 3. RoutingRulesPanel
**File**: `frontend/src/features/notifications/RoutingRulesPanel.tsx`

Convert routing rules table. Define columns:
- `channel_id` / channel name (sortable) — resolve from channel list if available
- `min_severity` (sortable) — severity badge
- `alert_type` (sortable) — text or "Any"
- `throttle_minutes` (sortable) — formatted duration
- `is_enabled` (sortable) — Switch or Badge
- `actions` (non-sortable) — Edit/Delete

**Empty state**: "No routing rules. Add a rule to control which alerts go to which channels."

---

## 4. ReportsPage
**File**: `frontend/src/features/reports/ReportsPage.tsx`

This page has TWO raw tables:
1. "Top Alerting Devices" — small summary table
2. "Recent Reports" — report runs table

Convert **both** to DataTable.

**Table 1 — Top Alerting Devices** columns:
- `device_id` (sortable) — monospace text
- `count` (sortable) — alert count number

**Table 2 — Recent Reports** columns:
- `type` (sortable)
- `status` (sortable) — Badge with status variant
- `triggered_by` (sortable)
- `rows` (sortable) — row count
- `started` (sortable) — formatted timestamp
- `duration` (sortable) — formatted duration

Both tables: client-side sorting, no pagination (small datasets).

---

## Verification
```bash
cd frontend && npm run build
npx tsc --noEmit
```
Visit each converted page and verify:
- Sorting works on sortable columns (click header to toggle)
- Loading skeleton shows when data is fetching
- Empty state shows when no data
- All action buttons (edit, delete) still work
- No visual regressions
