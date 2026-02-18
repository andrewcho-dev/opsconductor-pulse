import { useMemo, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { type ColumnDef } from "@tanstack/react-table";
import { DataTable } from "@/components/ui/data-table";
import { Button } from "@/components/ui/button";
import { Switch } from "@/components/ui/switch";
import { PageHeader, SeverityBadge, EmptyState } from "@/components/shared";
import { Pencil, Plus, ShieldAlert, Trash2 } from "lucide-react";
import { useAuth } from "@/services/auth/AuthProvider";
import {
  useAlertRules,
  useUpdateAlertRule,
} from "@/hooks/use-alert-rules";
import type { AlertRule } from "@/services/api/types";
import { AlertRuleDialog } from "./AlertRuleDialog";
import { DeleteAlertRuleDialog } from "./DeleteAlertRuleDialog";
import {
  applyAlertRuleTemplates,
  fetchAlertRuleTemplates,
} from "@/services/api/alert-rules";
import { toast } from "sonner";

const OPERATOR_LABELS: Record<string, string> = {
  GT: ">",
  LT: "<",
  GTE: "≥",
  LTE: "≤",
};

function makeColumns(
  isAdmin: boolean,
  formatCondition: (rule: AlertRule) => string,
  formatDuration: (rule: AlertRule) => string,
  onToggleEnabled: (rule: AlertRule, checked: boolean) => void,
  onEdit: (rule: AlertRule) => void,
  onDelete: (rule: AlertRule) => void,
): ColumnDef<AlertRule>[] {
  return [
    {
      accessorKey: "name",
      header: "Name",
      cell: ({ row }) => <span className="font-medium">{row.original.name}</span>,
    },
    {
      id: "condition",
      header: "Condition",
      enableSorting: false,
      cell: ({ row }) => (
        <span className="font-mono text-sm">{formatCondition(row.original)}</span>
      ),
    },
    {
      id: "duration",
      header: "Duration",
      cell: ({ row }) => formatDuration(row.original),
    },
    {
      accessorKey: "severity",
      header: "Severity",
      cell: ({ row }) => <SeverityBadge severity={row.original.severity} />,
    },
    {
      accessorKey: "enabled",
      header: "Enabled",
      cell: ({ row }) => (
        <Switch
          checked={row.original.enabled}
          onCheckedChange={(checked) => onToggleEnabled(row.original, checked)}
          disabled={!isAdmin}
        />
      ),
    },
    ...(isAdmin
      ? [
          {
            id: "actions",
            header: () => <span className="text-right">Actions</span>,
            enableSorting: false,
            cell: ({ row }: { row: { original: AlertRule } }) => (
              <div className="flex justify-end gap-1">
                <Button variant="ghost" size="sm" onClick={() => onEdit(row.original)}>
                  <Pencil className="mr-1 h-3.5 w-3.5" />
                  Edit
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  className="text-destructive"
                  onClick={() => onDelete(row.original)}
                >
                  <Trash2 className="mr-1 h-3.5 w-3.5" />
                  Delete
                </Button>
              </div>
            ),
          } as ColumnDef<AlertRule>,
        ]
      : []),
  ];
}

export default function AlertRulesPage() {
  const queryClient = useQueryClient();
  const { user } = useAuth();
  const isAdmin = user?.role === "customer_admin";

  const { data, isLoading, error } = useAlertRules(200);
  const updateRule = useUpdateAlertRule();

  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingRule, setEditingRule] = useState<AlertRule | null>(null);
  const [deletingRule, setDeletingRule] = useState<AlertRule | null>(null);
  const [applyingDefaults, setApplyingDefaults] = useState(false);

  const rules = data?.rules || [];
  const count = data?.count || rules.length;

  const description = isLoading ? "Loading..." : `${count} rules configured`;

  const emptyAction = isAdmin ? (
    <Button onClick={() => {
      setEditingRule(null);
      setDialogOpen(true);
    }}>
      <Plus className="mr-1 h-4 w-4" />
      Add Rule
    </Button>
  ) : undefined;

  const rows = useMemo(() => rules, [rules]);

  const columns = useMemo(
    () =>
      makeColumns(
        isAdmin,
        formatCondition,
        formatDuration,
        (rule, checked) => {
          if (!isAdmin) return;
          updateRule.mutate({ ruleId: String(rule.rule_id), data: { enabled: checked } });
        },
        (rule) => {
          setEditingRule(rule);
          setDialogOpen(true);
        },
        (rule) => setDeletingRule(rule),
      ),
    [isAdmin, updateRule, formatCondition, formatDuration],
  );

  async function handleAddAllDefaults() {
    setApplyingDefaults(true);
    try {
      const templates = await fetchAlertRuleTemplates();
      const result = await applyAlertRuleTemplates(
        templates.map((tmpl) => tmpl.template_id)
      );
      toast.success(`Created ${result.created.length} rules, skipped ${result.skipped.length} (already exist)`);
      await queryClient.invalidateQueries({ queryKey: ["alert-rules"] });
    } finally {
      setApplyingDefaults(false);
    }
  }

  function formatCondition(rule: AlertRule) {
    if (rule.rule_type === "window" && rule.aggregation && rule.window_seconds) {
      const op = OPERATOR_LABELS[rule.operator] || rule.operator;
      const windowDisplay =
        rule.window_seconds >= 60
          ? `${rule.window_seconds / 60}m`
          : `${rule.window_seconds}s`;
      return `${rule.aggregation}(${rule.metric_name}) ${op} ${rule.threshold} over ${windowDisplay}`;
    }
    if (Array.isArray(rule.conditions) && rule.conditions.length > 0) {
      if (rule.conditions.length === 1) {
        const condition = rule.conditions[0];
        const op = OPERATOR_LABELS[condition.operator] || condition.operator;
        return `${condition.metric_name} ${op} ${condition.threshold}`;
      }
      const joiner = rule.match_mode === "any" ? " OR " : " AND ";
      return rule.conditions
        .map((condition) => {
          const op = OPERATOR_LABELS[condition.operator] || condition.operator;
          return `${condition.metric_name} ${op} ${condition.threshold}`;
        })
        .join(joiner);
    }
    const op = OPERATOR_LABELS[rule.operator] || rule.operator;
    return `${rule.metric_name} ${op} ${rule.threshold}`;
  }

  function formatDuration(rule: AlertRule) {
    if (rule.duration_minutes != null && rule.duration_minutes > 0) {
      return `${rule.duration_minutes}m`;
    }
    const seconds = rule.duration_seconds ?? 0;
    if (seconds <= 0) return "Immediate";
    if (seconds % 60 === 0) return `${seconds / 60}m`;
    return `${seconds}s`;
  }

  return (
    <div className="space-y-4">
      <PageHeader
        title="Alert Rules"
        description={description}
        action={
          isAdmin ? (
            <div className="flex items-center gap-2">
              <Button
                variant="outline"
                disabled={applyingDefaults}
                onClick={handleAddAllDefaults}
              >
                {applyingDefaults ? "Applying..." : "Add All Defaults"}
              </Button>
              <Button
                onClick={() => {
                  setEditingRule(null);
                  setDialogOpen(true);
                }}
              >
                <Plus className="mr-1 h-4 w-4" />
                Add Rule
              </Button>
            </div>
          ) : undefined
        }
      />

      {error ? (
        <div className="text-destructive">
          Failed to load alert rules: {(error as Error).message}
        </div>
      ) : (
        <DataTable
          columns={columns}
          data={rows}
          isLoading={isLoading}
          emptyState={
            <EmptyState
              title="No alert rules"
              description="Create rules to trigger threshold alerts."
              icon={<ShieldAlert className="h-12 w-12" />}
              action={emptyAction}
            />
          }
        />
      )}

      <AlertRuleDialog
        open={dialogOpen}
        rule={editingRule}
        onClose={() => {
          setDialogOpen(false);
          setEditingRule(null);
        }}
      />

      <DeleteAlertRuleDialog
        open={!!deletingRule}
        rule={deletingRule}
        onClose={() => setDeletingRule(null)}
      />
    </div>
  );
}
