# 003 — Standardize Tables with @tanstack/react-table

## Context

Tables across the app use a mix of raw HTML `<table>`, CSS grid layouts, and the basic Shadcn `<Table>` wrapper. None have sortable columns or consistent pagination. This step installs `@tanstack/react-table`, creates a reusable `DataTable` component, and retrofits the four highest-priority table views.

---

## 3a — Install @tanstack/react-table

```bash
cd frontend && npm install @tanstack/react-table
```

---

## 3b — Create DataTable component

**File**: `frontend/src/components/ui/data-table.tsx` (new file)

```tsx
import {
  type ColumnDef,
  type SortingState,
  type PaginationState,
  type OnChangeFn,
  flexRender,
  getCoreRowModel,
  getSortedRowModel,
  useReactTable,
} from "@tanstack/react-table";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { ArrowDown, ArrowUp, ArrowUpDown } from "lucide-react";

interface DataTableProps<TData, TValue> {
  columns: ColumnDef<TData, TValue>[];
  data: TData[];
  /** Total row count for server-side pagination */
  totalCount?: number;
  /** Current pagination state (pageIndex is 0-based) */
  pagination?: PaginationState;
  /** Callback when pagination changes */
  onPaginationChange?: OnChangeFn<PaginationState>;
  /** Whether pagination is server-side (default: true when totalCount is provided) */
  manualPagination?: boolean;
  /** Loading state — shows skeleton rows */
  isLoading?: boolean;
  /** Number of skeleton rows to show when loading */
  skeletonRows?: number;
  /** Component to show when data is empty */
  emptyState?: React.ReactNode;
  /** Callback when a row is clicked */
  onRowClick?: (row: TData) => void;
}

export function DataTable<TData, TValue>({
  columns,
  data,
  totalCount,
  pagination,
  onPaginationChange,
  manualPagination,
  isLoading = false,
  skeletonRows = 5,
  emptyState,
  onRowClick,
}: DataTableProps<TData, TValue>) {
  const [sorting, setSorting] = React.useState<SortingState>([]);

  const isServerPagination = manualPagination ?? totalCount != null;

  const table = useReactTable({
    data,
    columns,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    onSortingChange: setSorting,
    state: {
      sorting,
      ...(pagination ? { pagination } : {}),
    },
    ...(isServerPagination
      ? {
          manualPagination: true,
          pageCount: totalCount != null && pagination
            ? Math.ceil(totalCount / pagination.pageSize)
            : -1,
          onPaginationChange,
        }
      : {}),
  });

  const pageIndex = pagination?.pageIndex ?? 0;
  const pageSize = pagination?.pageSize ?? data.length;
  const pageCount = table.getPageCount();

  if (isLoading) {
    return (
      <div className="rounded-md border border-border">
        <Table>
          <TableHeader>
            <TableRow>
              {columns.map((col, i) => (
                <TableHead key={i}>
                  <Skeleton className="h-4 w-20" />
                </TableHead>
              ))}
            </TableRow>
          </TableHeader>
          <TableBody>
            {Array.from({ length: skeletonRows }).map((_, rowIndex) => (
              <TableRow key={rowIndex}>
                {columns.map((_, colIndex) => (
                  <TableCell key={colIndex}>
                    <Skeleton className="h-4 w-full" />
                  </TableCell>
                ))}
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
    );
  }

  if (data.length === 0 && emptyState) {
    return <>{emptyState}</>;
  }

  return (
    <div className="space-y-4">
      <div className="rounded-md border border-border">
        <Table>
          <TableHeader>
            {table.getHeaderGroups().map((headerGroup) => (
              <TableRow key={headerGroup.id}>
                {headerGroup.headers.map((header) => (
                  <TableHead key={header.id}>
                    {header.isPlaceholder ? null : header.column.getCanSort() ? (
                      <button
                        className="flex items-center gap-1"
                        onClick={header.column.getToggleSortingHandler()}
                      >
                        {flexRender(header.column.columnDef.header, header.getContext())}
                        {header.column.getIsSorted() === "asc" ? (
                          <ArrowUp className="h-3.5 w-3.5" />
                        ) : header.column.getIsSorted() === "desc" ? (
                          <ArrowDown className="h-3.5 w-3.5" />
                        ) : (
                          <ArrowUpDown className="h-3.5 w-3.5 text-muted-foreground" />
                        )}
                      </button>
                    ) : (
                      flexRender(header.column.columnDef.header, header.getContext())
                    )}
                  </TableHead>
                ))}
              </TableRow>
            ))}
          </TableHeader>
          <TableBody>
            {table.getRowModel().rows.map((row) => (
              <TableRow
                key={row.id}
                data-state={row.getIsSelected() && "selected"}
                className={onRowClick ? "cursor-pointer" : ""}
                onClick={() => onRowClick?.(row.original)}
              >
                {row.getVisibleCells().map((cell) => (
                  <TableCell key={cell.id}>
                    {flexRender(cell.column.columnDef.cell, cell.getContext())}
                  </TableCell>
                ))}
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>

      {isServerPagination && pagination && onPaginationChange && (
        <div className="flex items-center justify-between">
          <div className="text-sm text-muted-foreground">
            Showing {pageIndex * pageSize + 1}–
            {Math.min((pageIndex + 1) * pageSize, totalCount ?? data.length)} of{" "}
            {totalCount ?? data.length}
          </div>
          <div className="flex items-center gap-2">
            <select
              value={pageSize}
              onChange={(e) =>
                onPaginationChange({
                  pageIndex: 0,
                  pageSize: Number(e.target.value),
                })
              }
              className="h-8 rounded border border-border bg-background px-2 text-sm"
            >
              {[10, 25, 50, 100].map((size) => (
                <option key={size} value={size}>
                  {size} / page
                </option>
              ))}
            </select>
            <Button
              variant="outline"
              size="sm"
              onClick={() => table.previousPage()}
              disabled={!table.getCanPreviousPage()}
            >
              Previous
            </Button>
            <span className="text-sm">
              Page {pageIndex + 1} of {pageCount > 0 ? pageCount : 1}
            </span>
            <Button
              variant="outline"
              size="sm"
              onClick={() => table.nextPage()}
              disabled={!table.getCanNextPage()}
            >
              Next
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}

import * as React from "react";
```

**Note**: The `import * as React` is at the bottom to work with the `React.useState` call within the component. Move it to the top of the file in the actual implementation — the code above groups the import with the component for readability in this prompt.

---

## 3c — Retrofit AlertRulesPage

**File**: `frontend/src/features/alerts/AlertRulesPage.tsx`

This page already uses the Shadcn `<Table>` component. Replace it with `DataTable`.

### Add imports:

```tsx
import { type ColumnDef } from "@tanstack/react-table";
import { DataTable } from "@/components/ui/data-table";
```

### Define columns outside the component:

```tsx
function makeColumns(
  isAdmin: boolean,
  formatCondition: (rule: AlertRule) => string,
  formatDuration: (rule: AlertRule) => string,
  onToggleEnabled: (rule: AlertRule, checked: boolean) => void,
  onEdit: (rule: AlertRule) => void,
  onDelete: (rule: AlertRule) => void,
): ColumnDef<AlertRule>[] {
  return [
    {
      accessorKey: "name",
      header: "Name",
      cell: ({ row }) => <span className="font-medium">{row.original.name}</span>,
    },
    {
      id: "condition",
      header: "Condition",
      enableSorting: false,
      cell: ({ row }) => (
        <span className="font-mono text-sm">{formatCondition(row.original)}</span>
      ),
    },
    {
      id: "duration",
      header: "Duration",
      cell: ({ row }) => formatDuration(row.original),
    },
    {
      accessorKey: "severity",
      header: "Severity",
      cell: ({ row }) => <SeverityBadge severity={row.original.severity} />,
    },
    {
      accessorKey: "enabled",
      header: "Enabled",
      cell: ({ row }) => (
        <Switch
          checked={row.original.enabled}
          onCheckedChange={(checked) => onToggleEnabled(row.original, checked)}
          disabled={!isAdmin}
        />
      ),
    },
    ...(isAdmin
      ? [
          {
            id: "actions",
            header: () => <span className="text-right">Actions</span>,
            enableSorting: false,
            cell: ({ row }: { row: { original: AlertRule } }) => (
              <div className="flex justify-end gap-2">
                <Button variant="outline" size="sm" onClick={() => onEdit(row.original)}>
                  Edit
                </Button>
                <Button variant="destructive" size="sm" onClick={() => onDelete(row.original)}>
                  Delete
                </Button>
              </div>
            ),
          } as ColumnDef<AlertRule>,
        ]
      : []),
  ];
}
```

### Inside the component, build columns with useMemo:

```tsx
const columns = useMemo(
  () =>
    makeColumns(
      isAdmin,
      formatCondition,
      formatDuration,
      (rule, checked) => {
        if (!isAdmin) return;
        updateRule.mutate({ ruleId: String(rule.rule_id), data: { enabled: checked } });
      },
      (rule) => {
        setEditingRule(rule);
        setDialogOpen(true);
      },
      (rule) => setDeletingRule(rule),
    ),
  [isAdmin, updateRule]
);
```

### Replace the table JSX block:

Remove the entire `<div className="rounded-md border border-border"><Table>...</Table></div>` block and replace with:

```tsx
<DataTable
  columns={columns}
  data={rows}
  isLoading={isLoading}
  emptyState={
    <EmptyState
      title="No alert rules"
      description="Create rules to trigger threshold alerts."
      icon={<ShieldAlert className="h-12 w-12" />}
      action={emptyAction}
    />
  }
/>
```

Remove the manual loading skeleton and empty state blocks since `DataTable` handles them.

Remove unused imports: `Table`, `TableBody`, `TableCell`, `TableHead`, `TableHeader`, `TableRow` (they are no longer directly used).

---

## 3d — Retrofit UsersPage

**File**: `frontend/src/features/users/UsersPage.tsx`

### Add imports:

```tsx
import { type ColumnDef, type PaginationState } from "@tanstack/react-table";
import { DataTable } from "@/components/ui/data-table";
```

### Define columns:

Define a `TenantUser` type (or import from the appropriate API types file) and create columns:

```tsx
const columns: ColumnDef<TenantUser>[] = [
  {
    accessorKey: "username",
    header: "Name",
    cell: ({ row }) => (
      <div>
        <div className="font-medium">
          {[row.original.first_name, row.original.last_name].filter(Boolean).join(" ") || row.original.username}
        </div>
        <div className="text-xs text-muted-foreground">@{row.original.username}</div>
      </div>
    ),
  },
  {
    accessorKey: "email",
    header: "Email",
    cell: ({ row }) => <span className="text-sm">{row.original.email}</span>,
  },
  {
    id: "role",
    header: "Role",
    cell: ({ row }) => (
      <Badge variant={row.original.roles?.includes("tenant-admin") ? "default" : "secondary"}>
        {getRoleLabel(row.original.roles || [])}
      </Badge>
    ),
  },
  {
    id: "status",
    header: "Status",
    cell: ({ row }) => (
      <Badge variant={row.original.enabled ? "outline" : "secondary"}>
        {row.original.enabled ? "Active" : "Disabled"}
      </Badge>
    ),
  },
  {
    id: "actions",
    enableSorting: false,
    cell: ({ row }) => {
      // render the existing DropdownMenu for this row
      // move the DropdownMenu JSX into this cell renderer
    },
  },
];
```

### Replace the `<Table>` block:

Replace the entire `<div className="rounded-md border"><Table>...</Table></div>` and the pagination block below it with:

```tsx
<DataTable
  columns={columns}
  data={users}
  totalCount={total}
  pagination={{ pageIndex: page - 1, pageSize: limit }}
  onPaginationChange={(updater) => {
    const next = typeof updater === "function"
      ? updater({ pageIndex: page - 1, pageSize: limit })
      : updater;
    setPage(next.pageIndex + 1);
  }}
  isLoading={isLoading}
  emptyState={
    <div className="py-12 text-center">
      <div className="mb-4 text-muted-foreground">No team members found.</div>
      <Button onClick={() => setInviteDialogOpen(true)}>
        <Plus className="mr-2 h-4 w-4" />
        Invite your first team member
      </Button>
    </div>
  }
/>
```

Remove unused imports: `Table`, `TableBody`, `TableCell`, `TableHead`, `TableHeader`, `TableRow`.

---

## 3e — Retrofit AlertListPage (keep grid layout, add server-side pagination)

**File**: `frontend/src/features/alerts/AlertListPage.tsx`

The AlertListPage uses a custom grid layout (not a `<table>`) which is appropriate for its inbox-style design. **Do NOT convert it to DataTable.** Instead, fix the pagination issue:

Currently the page fetches `200` alerts client-side and filters them. This is a scalability issue.

### Change:

1. Replace the hardcoded `200` limit with the current pagination state.
2. Add pagination controls at the bottom.

Add state:
```tsx
const [pageSize, setPageSize] = useState(25);
const [pageIndex, setPageIndex] = useState(0);
```

Update the main query (line 89):
```tsx
const { data, isLoading, error, refetch, isFetching } = useAlerts(
  activeApiStatus,
  pageSize,
  pageIndex * pageSize
);
```

Keep the `allOpenData` query at `limit: 1, offset: 0` just for counts (change from 200 to 1 since only `total` is needed):
```tsx
const { data: allOpenData } = useAlerts("OPEN", 1, 0);
```

Update `filteredAlerts` — since the server now handles pagination, you only need to filter by severity tab and search term. The client-side filtering on severity still applies since the API's `status` filter is separate from severity.

Add pagination controls at the bottom (after the alert grid), inside the main return:
```tsx
{!isLoading && filteredAlerts.length > 0 && (
  <div className="flex items-center justify-between">
    <span className="text-sm text-muted-foreground">
      Showing {pageIndex * pageSize + 1}–
      {Math.min((pageIndex + 1) * pageSize, data?.total ?? 0)} of {data?.total ?? 0}
    </span>
    <div className="flex items-center gap-2">
      <Button
        variant="outline"
        size="sm"
        onClick={() => setPageIndex((p) => Math.max(0, p - 1))}
        disabled={pageIndex === 0}
      >
        Previous
      </Button>
      <Button
        variant="outline"
        size="sm"
        onClick={() => setPageIndex((p) => p + 1)}
        disabled={(pageIndex + 1) * pageSize >= (data?.total ?? 0)}
      >
        Next
      </Button>
    </div>
  </div>
)}
```

Reset `pageIndex` to 0 when switching tabs:
```tsx
onClick={() => {
  setTab(item.key);
  setSearch("");
  setSelected(new Set());
  setPageIndex(0);
}}
```

---

## Commit

```bash
git add frontend/package.json frontend/package-lock.json \
  frontend/src/components/ui/data-table.tsx \
  frontend/src/features/alerts/AlertRulesPage.tsx \
  frontend/src/features/users/UsersPage.tsx \
  frontend/src/features/alerts/AlertListPage.tsx

git commit -m "feat: add DataTable component, retrofit tables with sorting and pagination"
```

## Verification

```bash
cd frontend && npm run build
# Expected: builds clean

cd frontend && npx tsc --noEmit
# Expected: zero type errors

grep "@tanstack/react-table" frontend/package.json
# Expected: in dependencies

grep "DataTable" frontend/src/features/alerts/AlertRulesPage.tsx
# Expected: shows DataTable usage

grep "DataTable" frontend/src/features/users/UsersPage.tsx
# Expected: shows DataTable usage
```
