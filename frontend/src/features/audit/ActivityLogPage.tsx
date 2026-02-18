import { Fragment, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Skeleton } from "@/components/ui/skeleton";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { PageHeader, EmptyState } from "@/components/shared";
import { useAuditLog } from "@/hooks/use-audit-log";
import { formatTimestamp } from "@/lib/format";
import { ScrollText } from "lucide-react";

function toIso(value: string): string | undefined {
  if (!value) return undefined;
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return undefined;
  return parsed.toISOString();
}

function getSeverityClass(severity: string): string {
  const normalized = severity.toLowerCase();
  if (normalized === "critical") return "text-red-700 border-red-200 dark:text-red-400 dark:border-red-700";
  if (normalized === "error") return "text-red-600 border-red-200 dark:text-red-400 dark:border-red-700";
  if (normalized === "warning") return "text-yellow-700 border-yellow-200 dark:text-yellow-400 dark:border-yellow-700";
  return "text-slate-700 border-slate-200 dark:text-slate-300 dark:border-slate-700";
}

function getEntityLink(entityType?: string | null, entityId?: string | null): string | null {
  if (!entityType || !entityId) return null;
  if (entityType === "device") return `/devices/${entityId}`;
  if (entityType === "alert") return "/alerts";
  if (entityType === "rule") return "/alert-rules";
  return null;
}

const PAGE_SIZES = [100, 250, 500, 1000];

function PaginationControls({
  offset,
  limit,
  totalCount,
  setOffset,
  setLimit,
}: {
  offset: number;
  limit: number;
  totalCount: number;
  setOffset: (n: number) => void;
  setLimit: (n: number) => void;
}) {
  return (
    <div className="flex items-center justify-between text-sm">
      <div className="flex items-center gap-2">
        <span className="text-muted-foreground">
          {totalCount > 0 ? `${offset + 1}-${Math.min(offset + limit, totalCount)}` : "0"} of {totalCount.toLocaleString()}
        </span>
        <select
          value={limit}
          onChange={(e) => {
            setLimit(Number(e.target.value));
            setOffset(0);
          }}
          className="h-6 px-1 rounded border border-border bg-background text-sm"
        >
          {PAGE_SIZES.map((size) => (
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
          className="px-2 py-0.5 rounded border border-border hover:bg-accent disabled:opacity-50 disabled:cursor-not-allowed text-sm"
        >
          First
        </button>
        <button
          onClick={() => setOffset(Math.max(0, offset - limit))}
          disabled={offset === 0}
          className="px-2 py-0.5 rounded border border-border hover:bg-accent disabled:opacity-50 disabled:cursor-not-allowed text-sm"
        >
          Prev
        </button>
        <button
          onClick={() => setOffset(offset + limit)}
          disabled={offset + limit >= totalCount}
          className="px-2 py-0.5 rounded border border-border hover:bg-accent disabled:opacity-50 disabled:cursor-not-allowed text-sm"
        >
          Next
        </button>
        <button
          onClick={() => setOffset(Math.max(0, Math.floor((totalCount - 1) / limit) * limit))}
          disabled={offset + limit >= totalCount}
          className="px-2 py-0.5 rounded border border-border hover:bg-accent disabled:opacity-50 disabled:cursor-not-allowed text-sm"
        >
          Last
        </button>
      </div>
    </div>
  );
}

export default function ActivityLogPage() {
  const [categoryInput, setCategoryInput] = useState("");
  const [severityInput, setSeverityInput] = useState("");
  const [searchInput, setSearchInput] = useState("");
  const [startInput, setStartInput] = useState("");
  const [endInput, setEndInput] = useState("");
  const [offset, setOffset] = useState(0);
  const [limit, setLimit] = useState(100);

  const [appliedFilters, setAppliedFilters] = useState({
    category: "",
    severity: "",
    search: "",
    start: "",
    end: "",
  });
  const { data, isLoading, error } = useAuditLog({
    limit,
    offset,
    category: appliedFilters.category || undefined,
    severity: appliedFilters.severity || undefined,
    search: appliedFilters.search || undefined,
    start: appliedFilters.start || undefined,
    end: appliedFilters.end || undefined,
  });

  const events = useMemo(() => data?.events || [], [data]);
  const totalCount = data?.total || 0;
  const [expanded, setExpanded] = useState<Set<string>>(new Set());

  function toggleExpanded(key: string) {
    setExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(key)) {
        next.delete(key);
      } else {
        next.add(key);
      }
      return next;
    });
  }

  return (
    <div className="space-y-4">
      <PageHeader
        title="Activity Log"
        description={
          isLoading
            ? "Loading..."
            : `${totalCount.toLocaleString()} event${totalCount === 1 ? "" : "s"}`
        }
      />

      <div className="flex flex-wrap gap-1.5 items-center">
        <Input
          value={categoryInput}
          onChange={(e) => setCategoryInput(e.target.value)}
          placeholder="Category"
          className="h-8 text-sm w-28"
        />
        <Input
          value={severityInput}
          onChange={(e) => setSeverityInput(e.target.value)}
          placeholder="Severity"
          className="h-8 text-sm w-24"
        />
        <Input
          value={startInput}
          onChange={(e) => setStartInput(e.target.value)}
          type="datetime-local"
          className="h-8 text-sm w-44"
        />
        <Input
          value={endInput}
          onChange={(e) => setEndInput(e.target.value)}
          type="datetime-local"
          className="h-8 text-sm w-44"
        />
        <Input
          value={searchInput}
          onChange={(e) => setSearchInput(e.target.value)}
          placeholder="Search"
          className="h-8 text-sm w-32"
        />
        <Button
          variant="outline"
          size="sm"
          className="h-8 text-sm"
          onClick={() => {
            setAppliedFilters({
              category: categoryInput.trim(),
              severity: severityInput.trim(),
              search: searchInput.trim(),
              start: toIso(startInput) || "",
              end: toIso(endInput) || "",
            });
            setOffset(0);
          }}
        >
          Filter
        </Button>
        <Button
          variant="ghost"
          size="sm"
          className="h-8 text-sm"
          onClick={() => {
            setCategoryInput("");
            setSeverityInput("");
            setSearchInput("");
            setStartInput("");
            setEndInput("");
            setAppliedFilters({
              category: "",
              severity: "",
              search: "",
              start: "",
              end: "",
            });
            setOffset(0);
          }}
        >
          Clear
        </Button>
      </div>

      {error ? (
        <div className="text-destructive">
          Failed to load activity log: {(error as Error).message}
        </div>
      ) : isLoading ? (
        <div className="space-y-1">
          {[1, 2, 3, 4, 5, 6, 7, 8].map((i) => (
            <Skeleton key={i} className="h-6 w-full" />
          ))}
        </div>
      ) : events.length === 0 ? (
        <EmptyState
          title="No activity"
          description="No audit events match the current filters."
          icon={<ScrollText className="h-12 w-12" />}
        />
      ) : (
        <>
          <PaginationControls
            offset={offset}
            limit={limit}
            totalCount={totalCount}
            setOffset={setOffset}
            setLimit={setLimit}
          />

          <div className="rounded-md border border-border overflow-hidden">
            <Table className="text-sm">
              <TableHeader>
                <TableRow className="hover:bg-transparent">
                  <TableHead className="h-8 py-1 px-2">Time</TableHead>
                  <TableHead className="h-8 py-1 px-2">Sev</TableHead>
                  <TableHead className="h-8 py-1 px-2">Category</TableHead>
                  <TableHead className="h-8 py-1 px-2">Message</TableHead>
                  <TableHead className="h-8 py-1 px-2">Entity</TableHead>
                  <TableHead className="h-8 py-1 px-2">Actor</TableHead>
                  <TableHead className="h-8 py-1 px-2 w-12"></TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {events.map((event, index) => {
                  const key = `${event.timestamp}-${event.event_type}-${event.entity_id ?? index}`;
                  const entityLink = getEntityLink(event.entity_type, event.entity_id);
                  return (
                    <Fragment key={key}>
                      <TableRow className="hover:bg-muted/50">
                        <TableCell className="py-1 px-2 text-muted-foreground whitespace-nowrap font-mono">
                          {formatTimestamp(event.timestamp)}
                        </TableCell>
                        <TableCell className="py-1 px-2">
                          <span className={`font-medium ${getSeverityClass(event.severity)}`}>
                            {event.severity.slice(0, 4)}
                          </span>
                        </TableCell>
                        <TableCell className="py-1 px-2">{event.category}</TableCell>
                        <TableCell className="py-1 px-2 max-w-md truncate">
                          {event.message}
                        </TableCell>
                        <TableCell className="py-1 px-2">
                          {entityLink ? (
                            <Link className="text-primary hover:underline" to={entityLink}>
                              {event.entity_name || event.entity_id}
                            </Link>
                          ) : (
                            event.entity_name || event.entity_id || "—"
                          )}
                        </TableCell>
                        <TableCell className="py-1 px-2">
                          {event.actor_name || event.actor_id || event.actor_type || "—"}
                        </TableCell>
                        <TableCell className="py-1 px-2 text-right">
                          {event.details && (
                            <button
                              className="text-primary hover:underline"
                              onClick={() => toggleExpanded(key)}
                            >
                              {expanded.has(key) ? "−" : "+"}
                            </button>
                          )}
                        </TableCell>
                      </TableRow>
                      {expanded.has(key) && (
                        <TableRow className="hover:bg-transparent">
                          <TableCell colSpan={7} className="py-1 px-2 bg-muted/30">
                            <pre className="whitespace-pre-wrap text-[11px] text-muted-foreground font-mono leading-tight">
                              {JSON.stringify(event.details, null, 2)}
                            </pre>
                          </TableCell>
                        </TableRow>
                      )}
                    </Fragment>
                  );
                })}
              </TableBody>
            </Table>
          </div>

          <PaginationControls
            offset={offset}
            limit={limit}
            totalCount={totalCount}
            setOffset={setOffset}
            setLimit={setLimit}
          />
        </>
      )}
    </div>
  );
}
