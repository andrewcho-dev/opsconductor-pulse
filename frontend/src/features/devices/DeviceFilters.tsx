import { useEffect, useState } from "react";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";

interface PaginationControlsProps {
  offset: number;
  limit: number;
  totalCount: number;
  setOffset: (n: number) => void;
  setLimit: (n: number) => void;
  showPagination?: boolean;
}

function PaginationControls({
  offset,
  limit,
  totalCount,
  setOffset,
  setLimit,
  showPagination = true,
}: PaginationControlsProps) {
  if (!showPagination) {
    return null;
  }
  return (
    <div className="flex items-center justify-between text-xs">
      <div className="flex items-center gap-2">
        <span className="text-muted-foreground">
          {totalCount > 0
            ? `${offset + 1}-${Math.min(offset + limit, totalCount)}`
            : "0"}{" "}
          of {totalCount.toLocaleString()}
        </span>
        <select
          value={limit}
          onChange={(e) => {
            setLimit(Number(e.target.value));
            setOffset(0);
          }}
          className="h-6 px-1 rounded border border-border bg-background text-xs"
          aria-label="Devices per page"
        >
          {[100, 250, 500, 1000].map((size) => (
            <option key={size} value={size}>
              {size} / page
            </option>
          ))}
        </select>
      </div>
      <div className="flex gap-1">
        <button
          onClick={() => setOffset(0)}
          disabled={offset === 0}
          className="px-2 py-0.5 rounded border border-border hover:bg-accent disabled:opacity-50 disabled:cursor-not-allowed text-xs"
          aria-label="First page"
        >
          First
        </button>
        <button
          onClick={() => setOffset(Math.max(0, offset - limit))}
          disabled={offset === 0}
          className="px-2 py-0.5 rounded border border-border hover:bg-accent disabled:opacity-50 disabled:cursor-not-allowed text-xs"
          aria-label="Previous page"
        >
          Prev
        </button>
        <button
          onClick={() => setOffset(offset + limit)}
          disabled={offset + limit >= totalCount}
          className="px-2 py-0.5 rounded border border-border hover:bg-accent disabled:opacity-50 disabled:cursor-not-allowed text-xs"
          aria-label="Next page"
        >
          Next
        </button>
        <button
          onClick={() =>
            setOffset(Math.max(0, Math.floor((totalCount - 1) / limit) * limit))
          }
          disabled={offset + limit >= totalCount}
          className="px-2 py-0.5 rounded border border-border hover:bg-accent disabled:opacity-50 disabled:cursor-not-allowed text-xs"
          aria-label="Last page"
        >
          Last
        </button>
      </div>
    </div>
  );
}

interface DeviceFiltersProps {
  selectedTags: string[];
  setSelectedTags: (tags: string[]) => void;
  allTags: string[];
  tagFilterOpen: boolean;
  setTagFilterOpen: (open: boolean) => void;
  toggleTag: (tag: string) => void;
  offset: number;
  limit: number;
  totalCount: number;
  setOffset: (n: number) => void;
  setLimit: (n: number) => void;
  q: string;
  onQChange: (q: string) => void;
  statusFilter: string;
  onStatusFilterChange: (s: string) => void;
  showPagination?: boolean;
}

export function DeviceFilters({
  selectedTags,
  setSelectedTags,
  allTags,
  tagFilterOpen,
  setTagFilterOpen,
  toggleTag,
  offset,
  limit,
  totalCount,
  setOffset,
  setLimit,
  q,
  onQChange,
  statusFilter,
  onStatusFilterChange,
  showPagination = true,
}: DeviceFiltersProps) {
  const [searchText, setSearchText] = useState(q);

  useEffect(() => {
    setSearchText(q);
  }, [q]);

  useEffect(() => {
    const timer = window.setTimeout(() => onQChange(searchText), 300);
    return () => window.clearTimeout(timer);
  }, [searchText, onQChange]);

  return (
    <>
      <div className="flex flex-wrap items-center gap-2">
        <div className="relative min-w-[280px] flex-1">
          <input
            type="text"
            value={searchText}
            onChange={(e) => setSearchText(e.target.value)}
            placeholder="Search by device ID, model, serial, site, or address"
            className="h-8 w-full rounded-md border border-border bg-background px-8 pr-8 text-sm"
            aria-label="Search devices"
          />
          <span className="pointer-events-none absolute left-2 top-1/2 -translate-y-1/2 text-muted-foreground">
            🔍
          </span>
          {searchText && (
            <button
              type="button"
              onClick={() => {
                setSearchText("");
                onQChange("");
              }}
              className="absolute right-2 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
              aria-label="Clear search"
            >
              ×
            </button>
          )}
        </div>

        <label className="sr-only" htmlFor="device-status-filter">
          Status filter
        </label>
        <select
          id="device-status-filter"
          value={statusFilter}
          onChange={(e) => onStatusFilterChange(e.target.value)}
          className="h-8 rounded-md border border-border bg-background px-2 text-sm"
          aria-label="Status filter"
        >
          <option value="">All statuses</option>
          <option value="ONLINE">Online</option>
          <option value="STALE">Stale</option>
          <option value="OFFLINE">Offline</option>
        </select>

        <div className="hidden items-center gap-2 text-xs text-muted-foreground md:flex">
          <span className="inline-flex items-center gap-1">
            <span className="h-2 w-2 rounded-full bg-green-500" />
            Online
          </span>
          <span className="inline-flex items-center gap-1">
            <span className="h-2 w-2 rounded-full bg-yellow-500" />
            Stale
          </span>
          <span className="inline-flex items-center gap-1">
            <span className="h-2 w-2 rounded-full bg-red-500" />
            Offline
          </span>
        </div>

        <Button
          variant="outline"
          size="sm"
          className="h-8"
          onClick={() => setTagFilterOpen(true)}
          aria-label="Open tag filters"
        >
          Tags {selectedTags.length > 0 ? `(${selectedTags.length})` : ""}
        </Button>
      </div>

      {selectedTags.length > 0 && (
        <div className="flex items-center gap-2">
          <span className="text-xs text-muted-foreground">
            Tags filter active ({selectedTags.length})
          </span>
          <button
            onClick={() => setSelectedTags([])}
            className="text-xs text-muted-foreground hover:text-foreground"
            aria-label="Clear tag filters"
          >
            Clear
          </button>
        </div>
      )}

      <Dialog open={tagFilterOpen} onOpenChange={setTagFilterOpen}>
        <DialogContent className="max-w-xs">
          <DialogHeader>
            <DialogTitle className="text-sm">Filter by Tags</DialogTitle>
          </DialogHeader>
          <div className="space-y-1 max-h-64 overflow-y-auto">
            {allTags.map((tag) => (
              <label
                key={tag}
                className="flex items-center gap-2 text-xs cursor-pointer hover:bg-muted p-1 rounded"
              >
                <input
                  type="checkbox"
                  checked={selectedTags.includes(tag)}
                  onChange={() => toggleTag(tag)}
                  className="h-3 w-3"
                  aria-label={`Filter by tag ${tag}`}
                />
                {tag}
              </label>
            ))}
            {allTags.length === 0 && (
              <div className="text-xs text-muted-foreground">No tags defined</div>
            )}
          </div>
          <div className="flex justify-end gap-2 pt-2 border-t">
            <Button
              variant="outline"
              size="sm"
              className="h-7 text-xs"
              onClick={() => setSelectedTags([])}
            >
              Clear All
            </Button>
            <Button
              size="sm"
              className="h-7 text-xs"
              onClick={() => setTagFilterOpen(false)}
            >
              Done
            </Button>
          </div>
        </DialogContent>
      </Dialog>

      <PaginationControls
        offset={offset}
        limit={limit}
        totalCount={totalCount}
        setOffset={setOffset}
        setLimit={setLimit}
        showPagination={showPagination}
      />
    </>
  );
}
