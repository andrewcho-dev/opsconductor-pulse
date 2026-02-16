import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { PageHeader } from "@/components/shared";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
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

  return (
    <div className="space-y-6">
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
            Add Channel
          </Button>
        }
      />

      <div className="overflow-x-auto rounded border border-border">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-border bg-muted/40">
              <th className="px-3 py-2 text-left">Name</th>
              <th className="px-3 py-2 text-left">Type</th>
              <th className="px-3 py-2 text-left">Status</th>
              <th className="px-3 py-2 text-left">Actions</th>
            </tr>
          </thead>
          <tbody>
            {channels.map((channel) => (
              <tr key={channel.channel_id} className="border-b border-border/50">
                <td className="px-3 py-2">
                  <span>{channel.name}</span>
                  {Boolean(
                    (channel.config as Record<string, unknown>)?.migrated_from_integration_id
                  ) && (
                    <Badge variant="outline" className="ml-2 text-xs text-muted-foreground">
                      Migrated
                    </Badge>
                  )}
                </td>
                <td className="px-3 py-2">{channel.channel_type}</td>
                <td className="px-3 py-2">{channel.is_enabled ? "Enabled" : "Disabled"}</td>
                <td className="px-3 py-2">
                  <div className="flex gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={async () => {
                        const result = await testMutation.mutateAsync(channel.channel_id);
                        if (result.ok) {
                          toast.success("Test sent successfully");
                        } else {
                          toast.error(`Test failed: ${result.error ?? "Unknown error"}`);
                        }
                      }}
                    >
                      Test
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => {
                        setEditing(channel);
                        setOpen(true);
                      }}
                    >
                      Edit
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setSelectedChannelId(channel.channel_id)}
                    >
                      History
                    </Button>
                    <Button
                      variant="destructive"
                      size="sm"
                      onClick={() => setConfirmDelete(channel.channel_id)}
                    >
                      Delete
                    </Button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

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
