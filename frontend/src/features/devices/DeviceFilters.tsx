import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";

interface PaginationControlsProps {
  offset: number;
  limit: number;
  totalCount: number;
  setOffset: (n: number) => void;
  setLimit: (n: number) => void;
}

function PaginationControls({
  offset,
  limit,
  totalCount,
  setOffset,
  setLimit,
}: PaginationControlsProps) {
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
}: DeviceFiltersProps) {
  return (
    <>
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
      />
    </>
  );
}
