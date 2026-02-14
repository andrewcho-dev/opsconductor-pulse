import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { PageHeader } from "@/components/shared";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  createEscalationPolicy,
  deleteEscalationPolicy,
  listEscalationPolicies,
  updateEscalationPolicy,
  type EscalationPolicy,
} from "@/services/api/escalation";
import { EscalationPolicyModal } from "./EscalationPolicyModal";

function relativeTime(ts: string): string {
  const date = new Date(ts);
  if (Number.isNaN(date.getTime())) return "-";
  const diffSec = Math.floor((Date.now() - date.getTime()) / 1000);
  if (diffSec < 60) return `${diffSec}s ago`;
  const mins = Math.floor(diffSec / 60);
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  return `${Math.floor(hours / 24)}d ago`;
}

export default function EscalationPoliciesPage() {
  const queryClient = useQueryClient();
  const [open, setOpen] = useState(false);
  const [editing, setEditing] = useState<EscalationPolicy | null>(null);

  const { data, isLoading } = useQuery({
    queryKey: ["escalation-policies"],
    queryFn: listEscalationPolicies,
  });

  const createMutation = useMutation({
    mutationFn: createEscalationPolicy,
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["escalation-policies"] });
    },
  });
  const updateMutation = useMutation({
    mutationFn: ({ id, body }: { id: number; body: Partial<EscalationPolicy> }) =>
      updateEscalationPolicy(id, body),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["escalation-policies"] });
    },
  });
  const deleteMutation = useMutation({
    mutationFn: deleteEscalationPolicy,
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["escalation-policies"] });
    },
  });

  const rows = useMemo(() => data?.policies ?? [], [data?.policies]);

  return (
    <div className="space-y-6">
      <PageHeader
        title="Escalation Policies"
        description="Define multi-level escalation actions for unacknowledged alerts."
        action={
          <Button
            onClick={() => {
              setEditing(null);
              setOpen(true);
            }}
          >
            New Policy
          </Button>
        }
      />

      <div className="overflow-x-auto rounded-md border border-border">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-border bg-muted/40 text-left">
              <th className="px-3 py-2">Name</th>
              <th className="px-3 py-2">Default</th>
              <th className="px-3 py-2"># Levels</th>
              <th className="px-3 py-2">Created</th>
              <th className="px-3 py-2">Actions</th>
            </tr>
          </thead>
          <tbody>
            {isLoading && (
              <tr>
                <td className="px-3 py-4 text-muted-foreground" colSpan={5}>
                  Loading policies...
                </td>
              </tr>
            )}
            {!isLoading && rows.length === 0 && (
              <tr>
                <td className="px-3 py-4 text-muted-foreground" colSpan={5}>
                  No escalation policies configured.
                </td>
              </tr>
            )}
            {rows.map((policy) => (
              <tr key={policy.policy_id} className="border-b border-border/60">
                <td className="px-3 py-2">
                  <div className="font-medium">{policy.name}</div>
                  {policy.description && (
                    <div className="text-xs text-muted-foreground">{policy.description}</div>
                  )}
                </td>
                <td className="px-3 py-2">
                  {policy.is_default ? <Badge>Default</Badge> : <Badge variant="outline">No</Badge>}
                </td>
                <td className="px-3 py-2">{policy.levels.length}</td>
                <td className="px-3 py-2 text-muted-foreground">{relativeTime(policy.created_at)}</td>
                <td className="px-3 py-2">
                  <div className="flex gap-2">
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => {
                        setEditing(policy);
                        setOpen(true);
                      }}
                    >
                      Edit
                    </Button>
                    <Button
                      size="sm"
                      variant="destructive"
                      onClick={async () => {
                        if (!window.confirm("Delete this escalation policy?")) return;
                        await deleteMutation.mutateAsync(policy.policy_id);
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

      <EscalationPolicyModal
        open={open}
        onOpenChange={setOpen}
        initialPolicy={editing}
        onSave={async (payload) => {
          if (editing) {
            await updateMutation.mutateAsync({ id: editing.policy_id, body: payload });
          } else {
            await createMutation.mutateAsync(payload);
          }
        }}
      />
    </div>
  );
}
