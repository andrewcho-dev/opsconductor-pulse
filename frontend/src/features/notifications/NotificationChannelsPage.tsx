import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { PageHeader } from "@/components/shared";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { DataTable } from "@/components/ui/data-table";
import { type ColumnDef } from "@tanstack/react-table";
import {
  DropdownMenu,
  DropdownMenuTrigger,
  DropdownMenuContent,
  DropdownMenuItem,
} from "@/components/ui/dropdown-menu";
import { MoreHorizontal, Plus } from "lucide-react";
import { toast } from "sonner";
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
import {
  createChannel,
  deleteChannel,
  listNotificationJobs,
  listChannels,
  listRoutingRules,
  testChannel,
  updateChannel,
  type NotificationChannel,
} from "@/services/api/notifications";
import { ChannelModal } from "./ChannelModal";
import { RoutingRulesPanel } from "./RoutingRulesPanel";

export default function NotificationChannelsPage() {
  const queryClient = useQueryClient();
  const [open, setOpen] = useState(false);
  const [editing, setEditing] = useState<NotificationChannel | null>(null);
  const [selectedChannelId, setSelectedChannelId] = useState<number | null>(null);
  const [confirmDelete, setConfirmDelete] = useState<number | null>(null);

  const channelsQuery = useQuery({
    queryKey: ["notification-channels"],
    queryFn: listChannels,
  });
  const rulesQuery = useQuery({
    queryKey: ["notification-routing-rules"],
    queryFn: listRoutingRules,
  });
  const jobsQuery = useQuery({
    queryKey: ["notification-jobs", selectedChannelId],
    queryFn: () => listNotificationJobs(selectedChannelId ?? undefined, undefined, 20),
  });

  const createMutation = useMutation({
    mutationFn: createChannel,
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["notification-channels"] });
    },
  });
  const updateMutation = useMutation({
    mutationFn: ({ id, body }: { id: number; body: Partial<NotificationChannel> }) =>
      updateChannel(id, body),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["notification-channels"] });
    },
  });
  const deleteMutation = useMutation({
    mutationFn: deleteChannel,
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["notification-channels"] });
    },
  });

  const testMutation = useMutation({
    mutationFn: testChannel,
  });

  const channels = channelsQuery.data?.channels ?? [];
  const rules = rulesQuery.data?.rules ?? [];

  const columns: ColumnDef<NotificationChannel>[] = [
    {
      accessorKey: "name",
      header: "Name",
      cell: ({ row }) => {
        const ch = row.original;
        const migrated = Boolean(
          (ch.config as Record<string, unknown>)?.migrated_from_integration_id
        );
        return (
          <div className="flex items-center gap-2">
            <span className="font-medium">{ch.name}</span>
            {migrated && (
              <Badge variant="outline" className="text-xs text-muted-foreground">
                Migrated
              </Badge>
            )}
          </div>
        );
      },
    },
    {
      accessorKey: "channel_type",
      header: "Type",
      cell: ({ row }) => (
        <Badge variant="outline" className="capitalize">
          {row.original.channel_type}
        </Badge>
      ),
    },
    {
      accessorKey: "is_enabled",
      header: "Enabled",
      cell: ({ row }) => (
        <Badge variant={row.original.is_enabled ? "default" : "secondary"}>
          {row.original.is_enabled ? "Enabled" : "Disabled"}
        </Badge>
      ),
    },
    {
      accessorKey: "created_at",
      header: "Created",
      cell: ({ row }) => (
        <span className="text-xs text-muted-foreground">
          {row.original.created_at
            ? new Date(row.original.created_at).toLocaleDateString()
            : "—"}
        </span>
      ),
    },
    {
      id: "actions",
      enableSorting: false,
      cell: ({ row }) => {
        const ch = row.original;
        return (
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="ghost" size="icon" aria-label="Open channel actions">
                <MoreHorizontal className="h-4 w-4" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuItem
                onClick={async () => {
                  const result = await testMutation.mutateAsync(ch.channel_id);
                  if (result.status === "ok" || result.ok) {
                    toast.success(result.message || "Test sent successfully");
                  } else {
                    toast.error(`Test failed: ${result.error ?? "Unknown error"}`);
                  }
                }}
              >
                Test
              </DropdownMenuItem>
              <DropdownMenuItem
                onClick={() => {
                  setEditing(ch);
                  setOpen(true);
                }}
              >
                Edit
              </DropdownMenuItem>
              <DropdownMenuItem onClick={() => setSelectedChannelId(ch.channel_id)}>
                History
              </DropdownMenuItem>
              <DropdownMenuItem
                variant="destructive"
                onClick={() => setConfirmDelete(ch.channel_id)}
              >
                Delete
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        );
      },
    },
  ];

  return (
    <div className="space-y-4">
      <PageHeader
        title="Notification Channels"
        description="Configure channels and alert routing rules."
        action={
          <Button
            onClick={() => {
              setEditing(null);
              setOpen(true);
            }}
          >
            <Plus className="mr-1 h-4 w-4" />
            Add Channel
          </Button>
        }
      />

      <DataTable
        columns={columns}
        data={channels}
        isLoading={channelsQuery.isLoading}
        emptyState={
          <div className="rounded-md border border-border py-8 text-center text-muted-foreground">
            No notification channels configured. Add a channel to start receiving alerts.
          </div>
        }
        manualPagination={false}
      />

      <RoutingRulesPanel channels={channels} rules={rules} />
      {selectedChannelId && (
        <div className="rounded border border-border p-3">
          <div className="mb-2 text-sm font-medium">Recent Deliveries</div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border bg-muted/40">
                  <th className="px-2 py-1 text-left">Job</th>
                  <th className="px-2 py-1 text-left">Alert</th>
                  <th className="px-2 py-1 text-left">Status</th>
                  <th className="px-2 py-1 text-left">Attempts</th>
                  <th className="px-2 py-1 text-left">Created</th>
                </tr>
              </thead>
              <tbody>
                {(jobsQuery.data?.jobs ?? []).map((job) => (
                  <tr key={job.job_id} className="border-b border-border/40">
                    <td className="px-2 py-1">{job.job_id}</td>
                    <td className="px-2 py-1">{job.alert_id}</td>
                    <td className="px-2 py-1">{job.status}</td>
                    <td className="px-2 py-1">{job.attempts}</td>
                    <td className="px-2 py-1">{new Date(job.created_at).toLocaleString()}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      <ChannelModal
        open={open}
        onOpenChange={setOpen}
        initial={editing}
        onSave={async (draft) => {
          if (editing) {
            await updateMutation.mutateAsync({ id: editing.channel_id, body: draft });
          } else {
            await createMutation.mutateAsync(draft);
          }
        }}
      />

      <AlertDialog open={!!confirmDelete} onOpenChange={(openState) => !openState && setConfirmDelete(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete Channel</AlertDialogTitle>
            <AlertDialogDescription>
              Are you sure you want to delete this notification channel? This cannot be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={async () => {
                if (confirmDelete) await deleteMutation.mutateAsync(confirmDelete);
                setConfirmDelete(null);
              }}
            >
              Delete
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
