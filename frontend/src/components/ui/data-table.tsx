import * as React from "react";

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
          pageCount:
            totalCount != null && pagination
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
      <div className="rounded-lg border border-border overflow-hidden">
        <Table>
          <TableHeader>
            <TableRow>
              {columns.map((_, i) => (
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
    <div className="space-y-3">
      <div className="rounded-lg border border-border overflow-hidden">
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
                        {flexRender(
                          header.column.columnDef.header,
                          header.getContext(),
                        )}
                        {header.column.getIsSorted() === "asc" ? (
                          <ArrowUp className="h-3.5 w-3.5" />
                        ) : header.column.getIsSorted() === "desc" ? (
                          <ArrowDown className="h-3.5 w-3.5" />
                        ) : (
                          <ArrowUpDown className="h-3.5 w-3.5 text-muted-foreground" />
                        )}
                      </button>
                    ) : (
                      flexRender(
                        header.column.columnDef.header,
                        header.getContext(),
                      )
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

