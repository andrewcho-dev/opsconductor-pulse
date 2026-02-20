import { useEffect, useState } from "react";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { ChevronsLeft, ChevronLeft, ChevronRight, ChevronsRight, X } from "lucide-react";

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
    <div className="flex items-center justify-between text-sm">
      <div className="flex items-center gap-2">
        <span className="text-muted-foreground">
          {totalCount > 0
            ? `${offset + 1}-${Math.min(offset + limit, totalCount)}`
            : "0"}{" "}
          of {totalCount.toLocaleString()}
        </span>
        <Select
          value={String(limit)}
          onValueChange={(v) => {
            setLimit(Number(v));
            setOffset(0);
          }}
        >
          <SelectTrigger className="h-6 w-[110px]" aria-label="Devices per page">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {[100, 250, 500, 1000].map((size) => (
              <SelectItem key={size} value={String(size)}>
                {size} / page
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>
      <div className="flex gap-1">
        <Button
          type="button"
          variant="outline"
          size="icon-sm"
          onClick={() => setOffset(0)}
          disabled={offset === 0}
          aria-label="First page"
        >
          <ChevronsLeft className="h-3.5 w-3.5" />
        </Button>
        <Button
          type="button"
          variant="outline"
          size="icon-sm"
          onClick={() => setOffset(Math.max(0, offset - limit))}
          disabled={offset === 0}
          aria-label="Previous page"
        >
          <ChevronLeft className="h-3.5 w-3.5" />
        </Button>
        <Button
          type="button"
          variant="outline"
          size="icon-sm"
          onClick={() => setOffset(offset + limit)}
          disabled={offset + limit >= totalCount}
          aria-label="Next page"
        >
          <ChevronRight className="h-3.5 w-3.5" />
        </Button>
        <Button
          type="button"
          variant="outline"
          size="icon-sm"
          onClick={() =>
            setOffset(Math.max(0, Math.floor((totalCount - 1) / limit) * limit))
          }
          disabled={offset + limit >= totalCount}
          aria-label="Last page"
        >
          <ChevronsRight className="h-3.5 w-3.5" />
        </Button>
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
            <Button
              type="button"
              onClick={() => {
                setSearchText("");
                onQChange("");
              }}
              variant="ghost"
              size="icon-sm"
              className="absolute right-2 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
              aria-label="Clear search"
            >
              <X className="h-3.5 w-3.5" />
            </Button>
          )}
        </div>

        <label className="sr-only" htmlFor="device-status-filter">
          Status filter
        </label>
        <Select
          value={statusFilter || "all"}
          onValueChange={(v) => onStatusFilterChange(v === "all" ? "" : v)}
        >
          <SelectTrigger
            id="device-status-filter"
            className="h-8 w-[150px]"
            aria-label="Status filter"
          >
            <SelectValue placeholder="All statuses" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All statuses</SelectItem>
            <SelectItem value="ONLINE">Online</SelectItem>
            <SelectItem value="STALE">Stale</SelectItem>
            <SelectItem value="OFFLINE">Offline</SelectItem>
          </SelectContent>
        </Select>

        <div className="hidden items-center gap-2 text-sm text-muted-foreground md:flex">
          <span className="inline-flex items-center gap-1">
            <span className="h-2 w-2 rounded-full bg-status-online" />
            Online
          </span>
          <span className="inline-flex items-center gap-1">
            <span className="h-2 w-2 rounded-full bg-status-stale" />
            Stale
          </span>
          <span className="inline-flex items-center gap-1">
            <span className="h-2 w-2 rounded-full bg-status-offline" />
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
          <span className="text-sm text-muted-foreground">
            Tags filter active ({selectedTags.length})
          </span>
          <Button
            type="button"
            onClick={() => setSelectedTags([])}
            variant="ghost"
            size="sm"
            className="h-7 px-2 text-muted-foreground hover:text-foreground"
            aria-label="Clear tag filters"
          >
            Clear
          </Button>
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
                className="flex items-center gap-2 text-sm cursor-pointer hover:bg-muted p-1 rounded"
              >
                <Checkbox
                  checked={selectedTags.includes(tag)}
                  onCheckedChange={() => toggleTag(tag)}
                  aria-label={`Filter by tag ${tag}`}
                />
                {tag}
              </label>
            ))}
            {allTags.length === 0 && (
              <div className="text-sm text-muted-foreground">No tags defined</div>
            )}
          </div>
          <div className="flex justify-end gap-2 pt-2 border-t">
            <Button
              variant="outline"
              size="sm"
              className="h-8 text-sm"
              onClick={() => setSelectedTags([])}
            >
              Clear All
            </Button>
            <Button
              size="sm"
              className="h-8 text-sm"
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
