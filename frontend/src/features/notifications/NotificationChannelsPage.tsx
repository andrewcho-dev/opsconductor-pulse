import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { PageHeader } from "@/components/shared";
import { Button } from "@/components/ui/button";
import {
  createChannel,
  deleteChannel,
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

  const channelsQuery = useQuery({
    queryKey: ["notification-channels"],
    queryFn: listChannels,
  });
  const rulesQuery = useQuery({
    queryKey: ["notification-routing-rules"],
    queryFn: listRoutingRules,
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
                <td className="px-3 py-2">{channel.name}</td>
                <td className="px-3 py-2">{channel.channel_type}</td>
                <td className="px-3 py-2">{channel.is_enabled ? "Enabled" : "Disabled"}</td>
                <td className="px-3 py-2">
                  <div className="flex gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={async () => {
                        const result = await testMutation.mutateAsync(channel.channel_id);
                        window.alert(result.ok ? "Test sent" : `Test failed: ${result.error ?? "Unknown error"}`);
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
                      variant="destructive"
                      size="sm"
                      onClick={async () => {
                        if (!window.confirm("Delete this channel?")) return;
                        await deleteMutation.mutateAsync(channel.channel_id);
                      }}
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
    </div>
  );
}
