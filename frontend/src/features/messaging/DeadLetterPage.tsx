import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { PageHeader } from "@/components/shared";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { toast } from "sonner";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  discardDeadLetter,
  fetchDeadLetterMessages,
  purgeDeadLetter,
  replayDeadLetter,
  replayDeadLetterBatch,
} from "@/services/api/deadLetter";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { getErrorMessage } from "@/lib/errors";

const LIMIT = 50;

function statusVariant(status: string): "secondary" | "destructive" | "default" {
  if (status === "FAILED") return "destructive";
  if (status === "REPLAYED") return "default";
  return "secondary";
}

export default function DeadLetterPage({ embedded }: { embedded?: boolean }) {
  const queryClient = useQueryClient();
  const [statusFilter, setStatusFilter] = useState<string>("FAILED");
  const [offset, setOffset] = useState(0);
  const [selected, setSelected] = useState<Set<number>>(new Set());
  const [confirmPurge, setConfirmPurge] = useState(false);

  const { data, isLoading, error } = useQuery({
    queryKey: ["dead-letter", statusFilter, offset],
    queryFn: () =>
      fetchDeadLetterMessages({
        status: statusFilter === "ALL" ? undefined : statusFilter,
        limit: LIMIT,
        offset,
      }),
  });

  const replayMutation = useMutation({
    mutationFn: replayDeadLetter,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["dead-letter"] });
      toast.success("Message replayed");
    },
    onError: (err: Error) => {
      toast.error(getErrorMessage(err) || "Failed to replay message");
    },
  });

  const batchReplayMutation = useMutation({
    mutationFn: (ids: number[]) => replayDeadLetterBatch(ids),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["dead-letter"] });
      setSelected(new Set());
      toast.success("Messages replayed");
    },
    onError: (err: Error) => {
      toast.error(getErrorMessage(err) || "Failed to replay messages");
    },
  });

  const discardMutation = useMutation({
    mutationFn: discardDeadLetter,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["dead-letter"] });
      toast.success("Message discarded");
    },
    onError: (err: Error) => {
      toast.error(getErrorMessage(err) || "Failed to discard message");
    },
  });

  const purgeMutation = useMutation({
    mutationFn: () => purgeDeadLetter(30),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["dead-letter"] });
      toast.success("Old messages purged");
    },
    onError: (err: Error) => {
      toast.error(getErrorMessage(err) || "Failed to purge messages");
    },
  });

  const messages = data?.messages ?? [];
  const total = data?.total ?? 0;

  const toggleSelect = (id: number) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const toggleAll = () => {
    const failedIds = messages.filter((m) => m.status === "FAILED").map((m) => m.id);
    if (selected.size === failedIds.length) setSelected(new Set());
    else setSelected(new Set(failedIds));
  };

  return (
    <div className="space-y-4">
      {!embedded && <PageHeader title="Dead Letter Queue" description={`${total} messages`} />}

      <div className="flex items-center gap-2 flex-wrap">
        <Select
          value={statusFilter}
          onValueChange={(v) => {
            setStatusFilter(v);
            setOffset(0);
          }}
        >
          <SelectTrigger className="w-[180px]">
            <SelectValue placeholder="Filter status" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="ALL">All</SelectItem>
            <SelectItem value="FAILED">Failed</SelectItem>
            <SelectItem value="REPLAYED">Replayed</SelectItem>
            <SelectItem value="DISCARDED">Discarded</SelectItem>
          </SelectContent>
        </Select>

        {selected.size > 0 && (
          <>
            <Button
              size="sm"
              onClick={() => batchReplayMutation.mutate([...selected])}
              disabled={batchReplayMutation.isPending}
            >
              Replay Selected ({selected.size})
            </Button>
            <Button
              size="sm"
              variant="outline"
              onClick={() => {
                [...selected].forEach((id) => discardMutation.mutate(id));
                setSelected(new Set());
              }}
              disabled={discardMutation.isPending}
            >
              Discard Selected
            </Button>
          </>
        )}

        <div className="ml-auto">
          <Button
            size="sm"
            variant="destructive"
            onClick={() => setConfirmPurge(true)}
            disabled={purgeMutation.isPending}
          >
            Purge Old
          </Button>
        </div>
      </div>

      {error ? (
        <div className="text-destructive">
          Failed to load dead letter messages: {(error as Error).message}
        </div>
      ) : (
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="w-8">
                <Checkbox
                  checked={
                    selected.size > 0 &&
                    selected.size === messages.filter((m) => m.status === "FAILED").length
                  }
                  onCheckedChange={toggleAll}
                />
              </TableHead>
              <TableHead>Timestamp</TableHead>
              <TableHead>Route</TableHead>
              <TableHead>Topic</TableHead>
              <TableHead>Error</TableHead>
              <TableHead>Attempts</TableHead>
              <TableHead>Status</TableHead>
              <TableHead>Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {isLoading ? (
              <TableRow>
                <TableCell colSpan={8} className="text-center py-8 text-muted-foreground">
                  Loading...
                </TableCell>
              </TableRow>
            ) : messages.length === 0 ? (
              <TableRow>
                <TableCell colSpan={8} className="text-center py-8 text-muted-foreground">
                  No dead letter messages
                </TableCell>
              </TableRow>
            ) : (
              messages.map((msg) => (
                <TableRow key={msg.id}>
                  <TableCell>
                    {msg.status === "FAILED" && (
                      <Checkbox
                        checked={selected.has(msg.id)}
                        onCheckedChange={() => toggleSelect(msg.id)}
                      />
                    )}
                  </TableCell>
                  <TableCell className="whitespace-nowrap text-sm">
                    {new Date(msg.created_at).toLocaleString()}
                  </TableCell>
                  <TableCell className="text-sm">
                    {msg.route_name ?? `Route #${msg.route_id ?? "?"}`}
                  </TableCell>
                  <TableCell className="text-sm font-mono max-w-[200px] truncate">
                    {msg.original_topic}
                  </TableCell>
                  <TableCell className="text-sm max-w-[300px] truncate text-destructive">
                    {msg.error_message}
                  </TableCell>
                  <TableCell className="text-sm">{msg.attempts}</TableCell>
                  <TableCell>
                    <Badge variant={statusVariant(msg.status)}>{msg.status}</Badge>
                  </TableCell>
                  <TableCell>
                    {msg.status === "FAILED" ? (
                      <div className="flex gap-1">
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => replayMutation.mutate(msg.id)}
                          disabled={replayMutation.isPending}
                        >
                          Replay
                        </Button>
                        <Button
                          size="sm"
                          variant="ghost"
                          onClick={() => discardMutation.mutate(msg.id)}
                          disabled={discardMutation.isPending}
                        >
                          Discard
                        </Button>
                      </div>
                    ) : msg.status === "REPLAYED" && msg.replayed_at ? (
                      <span className="text-xs text-muted-foreground">
                        {new Date(msg.replayed_at).toLocaleString()}
                      </span>
                    ) : null}
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      )}

      <div className="flex items-center justify-between">
        <span className="text-sm text-muted-foreground">
          Showing {total === 0 ? 0 : offset + 1}-{Math.min(offset + LIMIT, total)} of {total}
        </span>
        <div className="flex gap-2">
          <Button
            size="sm"
            variant="outline"
            disabled={offset === 0}
            onClick={() => setOffset(Math.max(0, offset - LIMIT))}
          >
            Previous
          </Button>
          <Button
            size="sm"
            variant="outline"
            disabled={offset + LIMIT >= total}
            onClick={() => setOffset(offset + LIMIT)}
          >
            Next
          </Button>
        </div>
      </div>

      <AlertDialog open={confirmPurge} onOpenChange={setConfirmPurge}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Purge Old Messages</AlertDialogTitle>
            <AlertDialogDescription>
              Purge all FAILED messages older than 30 days? This action cannot be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={() => purgeMutation.mutate()}
              disabled={purgeMutation.isPending}
            >
              Purge
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}

