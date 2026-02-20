import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { DataTable } from "@/components/ui/data-table";
import { type ColumnDef } from "@tanstack/react-table";
import { Switch } from "@/components/ui/switch";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { toast } from "sonner";
import {
  createRoutingRule,
  deleteRoutingRule,
  updateRoutingRule,
  type NotificationChannel,
  type RoutingRule,
} from "@/services/api/notifications";
import { getErrorMessage } from "@/lib/errors";

interface RoutingRulesPanelProps {
  channels: NotificationChannel[];
  rules: RoutingRule[];
}

export function RoutingRulesPanel({ channels, rules }: RoutingRulesPanelProps) {
  const queryClient = useQueryClient();
  const [draft, setDraft] = useState<Omit<RoutingRule, "rule_id">>({
    channel_id: 0,
    min_severity: undefined,
    alert_type: "",
    device_tag_key: "",
    device_tag_val: "",
    site_ids: [],
    device_prefixes: [],
    deliver_on: ["OPEN"],
    priority: 100,
    throttle_minutes: 0,
    is_enabled: true,
  });
  const [editingRuleId, setEditingRuleId] = useState<number | null>(null);

  const createMutation = useMutation({
    mutationFn: createRoutingRule,
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["notification-routing-rules"] });
      toast.success("Routing rule created");
    },
    onError: (err: Error) => {
      toast.error(getErrorMessage(err) || "Failed to create routing rule");
    },
  });
  const updateMutation = useMutation({
    mutationFn: ({ id, body }: { id: number; body: Partial<RoutingRule> }) =>
      updateRoutingRule(id, body),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["notification-routing-rules"] });
      toast.success("Routing rule updated");
    },
    onError: (err: Error) => {
      toast.error(getErrorMessage(err) || "Failed to update routing rule");
    },
  });
  const deleteMutation = useMutation({
    mutationFn: deleteRoutingRule,
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["notification-routing-rules"] });
      toast.success("Routing rule deleted");
    },
    onError: (err: Error) => {
      toast.error(getErrorMessage(err) || "Failed to delete routing rule");
    },
  });

  const channelName = (channelId: number) =>
    channels.find((c) => c.channel_id === channelId)?.name ?? String(channelId);

  const severityBadge = (severity?: number) => {
    if (severity == null) return <span className="text-muted-foreground">Any</span>;
    const variant =
      severity >= 5 ? "destructive" : severity >= 4 ? "secondary" : "outline";
    return <Badge variant={variant}>{severity}</Badge>;
  };

  const columns: ColumnDef<RoutingRule>[] = [
    {
      id: "channel",
      header: "Channel",
      accessorFn: (r) => channelName(r.channel_id),
      cell: ({ row }) => <span className="font-medium">{channelName(row.original.channel_id)}</span>,
    },
    {
      accessorKey: "min_severity",
      header: "Min Severity",
      cell: ({ row }) => severityBadge(row.original.min_severity),
    },
    {
      accessorKey: "alert_type",
      header: "Type",
      cell: ({ row }) => row.original.alert_type || "Any",
    },
    {
      accessorKey: "throttle_minutes",
      header: "Throttle",
      cell: ({ row }) =>
        row.original.throttle_minutes > 0
          ? `${row.original.throttle_minutes}m`
          : "None",
    },
    {
      accessorKey: "is_enabled",
      header: "Enabled",
      cell: ({ row }) => (
        <div className="flex items-center gap-2">
          <Switch
            checked={row.original.is_enabled}
            onCheckedChange={(next) =>
              updateMutation.mutate({ id: row.original.rule_id, body: { is_enabled: next } })
            }
          />
          <span className="text-xs text-muted-foreground">
            {row.original.is_enabled ? "Enabled" : "Disabled"}
          </span>
        </div>
      ),
    },
    {
      id: "actions",
      enableSorting: false,
      cell: ({ row }) => (
        <div className="flex gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => {
              const r = row.original;
              setEditingRuleId(r.rule_id);
              setDraft({
                channel_id: r.channel_id,
                min_severity: r.min_severity,
                alert_type: r.alert_type ?? "",
                device_tag_key: r.device_tag_key ?? "",
                device_tag_val: r.device_tag_val ?? "",
                site_ids: r.site_ids ?? [],
                device_prefixes: r.device_prefixes ?? [],
                deliver_on: r.deliver_on ?? ["OPEN"],
                priority: r.priority ?? 100,
                throttle_minutes: r.throttle_minutes ?? 0,
                is_enabled: r.is_enabled,
              });
            }}
          >
            Edit
          </Button>
          <Button
            variant="destructive"
            size="sm"
            onClick={async () => {
              await deleteMutation.mutateAsync(row.original.rule_id);
            }}
          >
            Delete
          </Button>
        </div>
      ),
    },
  ];

  return (
    <div className="space-y-3 rounded-md border border-border p-3">
      <div className="flex items-center justify-between">
        <h3 className="font-medium">Routing Rules</h3>
      </div>

      <div className="grid gap-2 md:grid-cols-10">
        <Select
          value={draft.channel_id ? String(draft.channel_id) : "none"}
          onValueChange={(v) => setDraft((prev) => ({ ...prev, channel_id: v === "none" ? 0 : Number(v) }))}
        >
          <SelectTrigger className="h-9">
            <SelectValue placeholder="Channel" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="none">Channel</SelectItem>
            {channels.map((channel) => (
              <SelectItem key={channel.channel_id} value={String(channel.channel_id)}>
                {channel.name}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Select
          value={draft.min_severity != null ? String(draft.min_severity) : "any"}
          onValueChange={(v) =>
            setDraft((prev) => ({ ...prev, min_severity: v === "any" ? undefined : Number(v) }))
          }
        >
          <SelectTrigger className="h-9">
            <SelectValue placeholder="Any severity" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="any">Any severity</SelectItem>
            <SelectItem value="1">LOW (1)</SelectItem>
            <SelectItem value="3">MEDIUM (3)</SelectItem>
            <SelectItem value="4">HIGH (4)</SelectItem>
            <SelectItem value="5">CRITICAL (5)</SelectItem>
          </SelectContent>
        </Select>
        <input
          className="h-9 rounded-md border border-input bg-background px-2 text-sm"
          placeholder="Alert type"
          value={draft.alert_type ?? ""}
          onChange={(e) => setDraft((prev) => ({ ...prev, alert_type: e.target.value }))}
        />
        <input
          className="h-9 rounded-md border border-input bg-background px-2 text-sm"
          placeholder="Tag key"
          value={draft.device_tag_key ?? ""}
          onChange={(e) => setDraft((prev) => ({ ...prev, device_tag_key: e.target.value }))}
        />
        <input
          className="h-9 rounded-md border border-input bg-background px-2 text-sm"
          placeholder="Tag value"
          value={draft.device_tag_val ?? ""}
          onChange={(e) => setDraft((prev) => ({ ...prev, device_tag_val: e.target.value }))}
        />
        <input
          className="h-9 rounded-md border border-input bg-background px-2 text-sm"
          placeholder="Site IDs (csv)"
          value={(draft.site_ids ?? []).join(",")}
          onChange={(e) =>
            setDraft((prev) => ({
              ...prev,
              site_ids: e.target.value
                .split(",")
                .map((entry) => entry.trim())
                .filter(Boolean),
            }))
          }
        />
        <input
          className="h-9 rounded-md border border-input bg-background px-2 text-sm"
          placeholder="Device prefixes (csv)"
          value={(draft.device_prefixes ?? []).join(",")}
          onChange={(e) =>
            setDraft((prev) => ({
              ...prev,
              device_prefixes: e.target.value
                .split(",")
                .map((entry) => entry.trim())
                .filter(Boolean),
            }))
          }
        />
        <Select
          value={(draft.deliver_on ?? ["OPEN"]).join(",")}
          onValueChange={(v) =>
            setDraft((prev) => ({
              ...prev,
              deliver_on: v.split(",").filter(Boolean),
            }))
          }
        >
          <SelectTrigger className="h-9">
            <SelectValue placeholder="Deliver on" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="OPEN">OPEN</SelectItem>
            <SelectItem value="OPEN,CLOSED">OPEN+CLOSED</SelectItem>
            <SelectItem value="OPEN,ACKNOWLEDGED">OPEN+ACKNOWLEDGED</SelectItem>
            <SelectItem value="OPEN,CLOSED,ACKNOWLEDGED">OPEN+CLOSED+ACKNOWLEDGED</SelectItem>
          </SelectContent>
        </Select>
        <input
          type="number"
          min={0}
          className="h-9 rounded-md border border-input bg-background px-2 text-sm"
          placeholder="Priority"
          value={draft.priority ?? 100}
          onChange={(e) => setDraft((prev) => ({ ...prev, priority: Number(e.target.value || 100) }))}
        />
        <div className="flex gap-2">
          <input
            type="number"
            min={0}
            className="h-9 w-full rounded-md border border-input bg-background px-2 text-sm"
            placeholder="Throttle min"
            value={draft.throttle_minutes}
            onChange={(e) =>
              setDraft((prev) => ({ ...prev, throttle_minutes: Number(e.target.value || 0) }))
            }
          />
          <Button
            onClick={async () => {
              if (!draft.channel_id) return;
              const payload: Omit<RoutingRule, "rule_id"> = {
                ...draft,
                alert_type: draft.alert_type || undefined,
                device_tag_key: draft.device_tag_key || undefined,
                device_tag_val: draft.device_tag_val || undefined,
                site_ids: draft.site_ids?.length ? draft.site_ids : undefined,
                device_prefixes: draft.device_prefixes?.length ? draft.device_prefixes : undefined,
              };
              if (editingRuleId != null) {
                await updateMutation.mutateAsync({ id: editingRuleId, body: payload });
                setEditingRuleId(null);
              } else {
                await createMutation.mutateAsync(payload);
              }
            }}
          >
            {editingRuleId != null ? "Save" : "Add"}
          </Button>
        </div>
      </div>

      <DataTable
        columns={columns}
        data={rules}
        isLoading={false}
        emptyState={
          <div className="rounded-md border border-border py-8 text-center text-muted-foreground">
            No routing rules. Add a rule to control which alerts go to which channels.
          </div>
        }
        manualPagination={false}
      />
    </div>
  );
}
