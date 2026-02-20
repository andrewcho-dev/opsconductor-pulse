import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { PageHeader } from "@/components/shared";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { DataTable } from "@/components/ui/data-table";
import { type ColumnDef } from "@tanstack/react-table";
import { Plus } from "lucide-react";
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
  createEscalationPolicy,
  deleteEscalationPolicy,
  listEscalationPolicies,
  updateEscalationPolicy,
  type EscalationPolicy,
} from "@/services/api/escalation";
import { EscalationPolicyModal } from "./EscalationPolicyModal";
import { getErrorMessage } from "@/lib/errors";

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

export default function EscalationPoliciesPage({ embedded }: { embedded?: boolean }) {
  const queryClient = useQueryClient();
  const [open, setOpen] = useState(false);
  const [editing, setEditing] = useState<EscalationPolicy | null>(null);
  const [confirmDeletePolicy, setConfirmDeletePolicy] = useState<EscalationPolicy | null>(null);

  const { data, isLoading } = useQuery({
    queryKey: ["escalation-policies"],
    queryFn: listEscalationPolicies,
  });

  const createMutation = useMutation({
    mutationFn: createEscalationPolicy,
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["escalation-policies"] });
      toast.success("Escalation policy created");
    },
    onError: (err: Error) => {
      toast.error(getErrorMessage(err) || "Failed to create escalation policy");
    },
  });
  const updateMutation = useMutation({
    mutationFn: ({ id, body }: { id: number; body: Partial<EscalationPolicy> }) =>
      updateEscalationPolicy(id, body),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["escalation-policies"] });
      toast.success("Escalation policy updated");
    },
    onError: (err: Error) => {
      toast.error(getErrorMessage(err) || "Failed to update escalation policy");
    },
  });
  const deleteMutation = useMutation({
    mutationFn: deleteEscalationPolicy,
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["escalation-policies"] });
      toast.success("Escalation policy deleted");
    },
    onError: (err: Error) => {
      toast.error(getErrorMessage(err) || "Failed to delete escalation policy");
    },
  });

  const rows = useMemo(() => data?.policies ?? [], [data?.policies]);

  const columns: ColumnDef<EscalationPolicy>[] = [
    {
      accessorKey: "name",
      header: "Name",
      cell: ({ row }) => (
        <div>
          <div className="font-medium">{row.original.name}</div>
          {row.original.description && (
            <div className="text-xs text-muted-foreground">{row.original.description}</div>
          )}
        </div>
      ),
    },
    {
      accessorKey: "is_default",
      header: "Default",
      cell: ({ row }) => (row.original.is_default ? <Badge>Default</Badge> : null),
    },
    {
      id: "levels_count",
      header: "# Levels",
      accessorFn: (p) => p.levels?.length ?? 0,
      cell: ({ getValue }) => <span>{String(getValue() ?? 0)}</span>,
    },
    {
      accessorKey: "created_at",
      header: "Created",
      cell: ({ row }) => (
        <span className="text-muted-foreground">{relativeTime(row.original.created_at)}</span>
      ),
    },
    {
      id: "actions",
      enableSorting: false,
      cell: ({ row }) => {
        const policy = row.original;
        return (
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
              onClick={() => setConfirmDeletePolicy(policy)}
            >
              Delete
            </Button>
          </div>
        );
      },
    },
  ];

  const actions = (
    <Button
      onClick={() => {
        setEditing(null);
        setOpen(true);
      }}
    >
      <Plus className="mr-1 h-4 w-4" />
      Add Policy
    </Button>
  );

  return (
    <div className="space-y-4">
      {!embedded ? (
        <PageHeader
          title="Escalation Policies"
          description="Define multi-level escalation actions for unacknowledged alerts."
          action={actions}
        />
      ) : (
        <div className="flex justify-end gap-2 mb-4">{actions}</div>
      )}

      <DataTable
        columns={columns}
        data={rows}
        isLoading={isLoading}
        emptyState={
          <div className="rounded-md border border-border py-8 text-center text-muted-foreground">
            No escalation policies configured. Create a policy to define alert escalation behavior.
          </div>
        }
        manualPagination={false}
      />

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

      <AlertDialog open={!!confirmDeletePolicy} onOpenChange={(openState) => !openState && setConfirmDeletePolicy(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete Escalation Policy</AlertDialogTitle>
            <AlertDialogDescription>
              Delete this escalation policy? This action cannot be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={async () => {
                if (confirmDeletePolicy) await deleteMutation.mutateAsync(confirmDeletePolicy.policy_id);
                setConfirmDeletePolicy(null);
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
