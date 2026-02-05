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
import { useAuth } from "@/services/auth/AuthProvider";
import { useAuditLog } from "@/hooks/use-operator";
import { FileText } from "lucide-react";

function formatTimestamp(ts: string): string {
  try {
    return new Date(ts).toLocaleString();
  } catch {
    return ts;
  }
}

export default function AuditLogPage() {
  const { user } = useAuth();
  const isAdmin = user?.role === "operator_admin";

  const [userInput, setUserInput] = useState("");
  const [actionInput, setActionInput] = useState("");
  const [appliedUser, setAppliedUser] = useState<string | undefined>(undefined);
  const [appliedAction, setAppliedAction] = useState<string | undefined>(undefined);

  const { data, isLoading, error } = useAuditLog(
    appliedUser,
    appliedAction,
    undefined,
    100
  );

  const entries = useMemo(() => data?.entries || [], [data]);

  if (!isAdmin) {
    return (
      <div className="space-y-6">
        <PageHeader title="Audit Log" description="Operator access events" />
        <div className="rounded-md border border-border p-6 text-sm text-muted-foreground">
          Audit log requires operator_admin role.
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <PageHeader title="Audit Log" description="Operator access events" />

      <div className="flex flex-wrap gap-2">
        <Input
          value={userInput}
          onChange={(e) => setUserInput(e.target.value)}
          placeholder="Filter by user ID"
          className="max-w-xs"
        />
        <Input
          value={actionInput}
          onChange={(e) => setActionInput(e.target.value)}
          placeholder="Filter by action"
          className="max-w-xs"
        />
        <Button
          variant="outline"
          onClick={() => {
            setAppliedUser(userInput.trim() || undefined);
            setAppliedAction(actionInput.trim() || undefined);
          }}
        >
          Filter
        </Button>
        <Button
          variant="ghost"
          onClick={() => {
            setUserInput("");
            setActionInput("");
            setAppliedUser(undefined);
            setAppliedAction(undefined);
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
        <div className="space-y-2">
          {[1, 2, 3, 4, 5].map((i) => (
            <Skeleton key={i} className="h-12 w-full" />
          ))}
        </div>
      ) : entries.length === 0 ? (
        <EmptyState
          title="No audit events"
          description="No operator access events match the current filters."
          icon={<FileText className="h-12 w-12" />}
        />
      ) : (
        <div className="rounded-md border border-border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Timestamp</TableHead>
                <TableHead>User</TableHead>
                <TableHead>Action</TableHead>
                <TableHead>Tenant</TableHead>
                <TableHead>Resource</TableHead>
                <TableHead>RLS</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {entries.map((entry) => {
                const resource =
                  entry.resource_type || entry.resource_id
                    ? `${entry.resource_type ?? "resource"}:${entry.resource_id ?? ""}`
                    : "—";
                return (
                  <TableRow key={entry.id}>
                    <TableCell className="text-xs text-muted-foreground whitespace-nowrap">
                      {formatTimestamp(entry.created_at)}
                    </TableCell>
                    <TableCell className="font-mono text-xs">
                      {entry.user_id}
                    </TableCell>
                    <TableCell className="text-xs">{entry.action}</TableCell>
                    <TableCell className="text-xs">
                      {entry.tenant_filter || "—"}
                    </TableCell>
                    <TableCell className="text-xs">{resource}</TableCell>
                    <TableCell>
                      <Badge variant={entry.rls_bypassed ? "destructive" : "outline"}>
                        {entry.rls_bypassed ? "Yes" : "No"}
                      </Badge>
                    </TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        </div>
      )}
    </div>
  );
}
