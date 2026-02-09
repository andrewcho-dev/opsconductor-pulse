import { useMemo, useState } from "react";
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
import { Badge } from "@/components/ui/badge";
import { PageHeader, EmptyState } from "@/components/shared";
import { useAuditLog } from "@/hooks/use-operator";
import { FileText } from "lucide-react";

const PAGE_SIZES = [100, 250, 500, 1000];

function formatTimestamp(ts: string): string {
  try {
    // Extract microseconds from ISO timestamp (JS Date only has ms precision)
    const fracMatch = ts.match(/\.(\d+)/);
    const micros = fracMatch ? fracMatch[1].padEnd(6, "0").slice(0, 6) : "000000";

    // Convert to local time
    const d = new Date(ts);
    const y = d.getFullYear();
    const m = String(d.getMonth() + 1).padStart(2, "0");
    const day = String(d.getDate()).padStart(2, "0");
    const hh = String(d.getHours()).padStart(2, "0");
    const mm = String(d.getMinutes()).padStart(2, "0");
    const ss = String(d.getSeconds()).padStart(2, "0");

    return `${y}-${m}-${day} ${hh}:${mm}:${ss}.${micros}`;
  } catch {
    return ts;
  }
}

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
    <div className="flex items-center justify-between text-xs">
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
          className="h-6 px-1 rounded border border-border bg-background text-xs"
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
          className="px-2 py-0.5 rounded border border-border hover:bg-accent disabled:opacity-50 disabled:cursor-not-allowed text-xs"
        >
          First
        </button>
        <button
          onClick={() => setOffset(Math.max(0, offset - limit))}
          disabled={offset === 0}
          className="px-2 py-0.5 rounded border border-border hover:bg-accent disabled:opacity-50 disabled:cursor-not-allowed text-xs"
        >
          Prev
        </button>
        <button
          onClick={() => setOffset(offset + limit)}
          disabled={offset + limit >= totalCount}
          className="px-2 py-0.5 rounded border border-border hover:bg-accent disabled:opacity-50 disabled:cursor-not-allowed text-xs"
        >
          Next
        </button>
        <button
          onClick={() => setOffset(Math.max(0, Math.floor((totalCount - 1) / limit) * limit))}
          disabled={offset + limit >= totalCount}
          className="px-2 py-0.5 rounded border border-border hover:bg-accent disabled:opacity-50 disabled:cursor-not-allowed text-xs"
        >
          Last
        </button>
      </div>
    </div>
  );
}

export default function AuditLogPage() {
  const [userInput, setUserInput] = useState("");
  const [actionInput, setActionInput] = useState("");
  const [appliedUser, setAppliedUser] = useState<string | undefined>(undefined);
  const [appliedAction, setAppliedAction] = useState<string | undefined>(undefined);
  const [limit, setLimit] = useState(100);
  const [offset, setOffset] = useState(0);

  const { data, isLoading, error } = useAuditLog(
    appliedUser,
    appliedAction,
    undefined,
    limit,
    offset
  );

  const entries = useMemo(() => data?.entries || [], [data]);
  const totalCount = data?.total || 0;

  return (
    <div className="space-y-3">
      <PageHeader
        title="Audit Log"
        description={
          isLoading
            ? "Loading..."
            : `${totalCount.toLocaleString()} event${totalCount === 1 ? "" : "s"}`
        }
      />

      <div className="flex flex-wrap gap-1.5 items-center">
        <Input
          value={userInput}
          onChange={(e) => setUserInput(e.target.value)}
          placeholder="User ID"
          className="h-8 text-xs w-32"
        />
        <Input
          value={actionInput}
          onChange={(e) => setActionInput(e.target.value)}
          placeholder="Action"
          className="h-8 text-xs w-28"
        />
        <Button
          variant="outline"
          size="sm"
          className="h-8 text-xs"
          onClick={() => {
            setAppliedUser(userInput.trim() || undefined);
            setAppliedAction(actionInput.trim() || undefined);
            setOffset(0);
          }}
        >
          Filter
        </Button>
        <Button
          variant="ghost"
          size="sm"
          className="h-8 text-xs"
          onClick={() => {
            setUserInput("");
            setActionInput("");
            setAppliedUser(undefined);
            setAppliedAction(undefined);
            setOffset(0);
          }}
        >
          Clear
        </Button>
      </div>

      {error ? (
        <div className="text-destructive">
          Failed to load audit log: {(error as Error).message}
        </div>
      ) : isLoading ? (
        <div className="space-y-1">
          {[1, 2, 3, 4, 5, 6, 7, 8].map((i) => (
            <Skeleton key={i} className="h-6 w-full" />
          ))}
        </div>
      ) : entries.length === 0 ? (
        <EmptyState
          title="No audit events"
          description="No operator access events match the current filters."
          icon={<FileText className="h-12 w-12" />}
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
            <Table className="text-xs">
              <TableHeader>
                <TableRow className="hover:bg-transparent">
                  <TableHead className="h-8 py-1 px-2">Time</TableHead>
                  <TableHead className="h-8 py-1 px-2">User</TableHead>
                  <TableHead className="h-8 py-1 px-2">Action</TableHead>
                  <TableHead className="h-8 py-1 px-2">Tenant</TableHead>
                  <TableHead className="h-8 py-1 px-2">Resource</TableHead>
                  <TableHead className="h-8 py-1 px-2">RLS</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {entries.map((entry) => {
                  const resource =
                    entry.resource_type || entry.resource_id
                      ? `${entry.resource_type ?? ""}:${entry.resource_id ?? ""}`
                      : "—";
                  return (
                    <TableRow key={entry.id} className="hover:bg-muted/50">
                      <TableCell className="py-1 px-2 text-muted-foreground whitespace-nowrap font-mono">
                        {formatTimestamp(entry.created_at)}
                      </TableCell>
                      <TableCell className="py-1 px-2 font-mono">
                        {entry.user_id}
                      </TableCell>
                      <TableCell className="py-1 px-2">{entry.action}</TableCell>
                      <TableCell className="py-1 px-2">
                        {entry.tenant_filter || "—"}
                      </TableCell>
                      <TableCell className="py-1 px-2">{resource}</TableCell>
                      <TableCell className="py-1 px-2">
                        <Badge
                          variant={entry.rls_bypassed ? "destructive" : "outline"}
                          className="text-[10px] px-1 py-0"
                        >
                          {entry.rls_bypassed ? "Yes" : "No"}
                        </Badge>
                      </TableCell>
                    </TableRow>
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
