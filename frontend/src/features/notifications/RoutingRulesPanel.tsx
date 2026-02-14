import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import {
  createRoutingRule,
  deleteRoutingRule,
  type NotificationChannel,
  type RoutingRule,
} from "@/services/api/notifications";

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
    throttle_minutes: 0,
    is_enabled: true,
  });

  const createMutation = useMutation({
    mutationFn: createRoutingRule,
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["notification-routing-rules"] });
    },
  });
  const deleteMutation = useMutation({
    mutationFn: deleteRoutingRule,
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["notification-routing-rules"] });
    },
  });

  return (
    <div className="space-y-3 rounded-md border border-border p-3">
      <div className="flex items-center justify-between">
        <h3 className="font-medium">Routing Rules</h3>
      </div>

      <div className="grid gap-2 md:grid-cols-6">
        <select
          className="h-9 rounded-md border border-input bg-background px-2 text-sm"
          value={draft.channel_id || ""}
          onChange={(e) => setDraft((prev) => ({ ...prev, channel_id: Number(e.target.value) }))}
        >
          <option value="">Channel</option>
          {channels.map((channel) => (
            <option key={channel.channel_id} value={channel.channel_id}>
              {channel.name}
            </option>
          ))}
        </select>
        <select
          className="h-9 rounded-md border border-input bg-background px-2 text-sm"
          value={draft.min_severity ?? ""}
          onChange={(e) =>
            setDraft((prev) => ({
              ...prev,
              min_severity: e.target.value ? Number(e.target.value) : undefined,
            }))
          }
        >
          <option value="">Any severity</option>
          <option value="1">LOW (1)</option>
          <option value="3">MEDIUM (3)</option>
          <option value="4">HIGH (4)</option>
          <option value="5">CRITICAL (5)</option>
        </select>
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
              await createMutation.mutateAsync({
                ...draft,
                alert_type: draft.alert_type || undefined,
                device_tag_key: draft.device_tag_key || undefined,
                device_tag_val: draft.device_tag_val || undefined,
              });
            }}
          >
            Add
          </Button>
        </div>
      </div>

      <div className="overflow-x-auto rounded border border-border">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-border bg-muted/40">
              <th className="px-2 py-1 text-left">Channel</th>
              <th className="px-2 py-1 text-left">Min Severity</th>
              <th className="px-2 py-1 text-left">Type</th>
              <th className="px-2 py-1 text-left">Throttle</th>
              <th className="px-2 py-1 text-left">Actions</th>
            </tr>
          </thead>
          <tbody>
            {rules.map((rule) => (
              <tr key={rule.rule_id} className="border-b border-border/40">
                <td className="px-2 py-1">
                  {channels.find((c) => c.channel_id === rule.channel_id)?.name ?? rule.channel_id}
                </td>
                <td className="px-2 py-1">{rule.min_severity ?? "any"}</td>
                <td className="px-2 py-1">{rule.alert_type ?? "any"}</td>
                <td className="px-2 py-1">{rule.throttle_minutes}m</td>
                <td className="px-2 py-1">
                  <Button
                    variant="destructive"
                    size="sm"
                    onClick={async () => {
                      await deleteMutation.mutateAsync(rule.rule_id);
                    }}
                  >
                    Delete
                  </Button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
