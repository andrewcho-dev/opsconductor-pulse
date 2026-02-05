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
import { Switch } from "@/components/ui/switch";
import { PageHeader, SeverityBadge, EmptyState } from "@/components/shared";
import { ShieldAlert } from "lucide-react";
import { useAuth } from "@/services/auth/AuthProvider";
import {
  useAlertRules,
  useUpdateAlertRule,
} from "@/hooks/use-alert-rules";
import type { AlertRule } from "@/services/api/types";
import { AlertRuleDialog } from "./AlertRuleDialog";
import { DeleteAlertRuleDialog } from "./DeleteAlertRuleDialog";

const OPERATOR_LABELS: Record<string, string> = {
  GT: ">",
  LT: "<",
  GTE: "≥",
  LTE: "≤",
};

export default function AlertRulesPage() {
  const { user } = useAuth();
  const isAdmin = user?.role === "customer_admin";

  const { data, isLoading, error } = useAlertRules(200);
  const updateRule = useUpdateAlertRule();

  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingRule, setEditingRule] = useState<AlertRule | null>(null);
  const [deletingRule, setDeletingRule] = useState<AlertRule | null>(null);

  const rules = data?.rules || [];
  const count = data?.count || rules.length;

  const description = isLoading ? "Loading..." : `${count} rules configured`;

  const emptyAction = isAdmin ? (
    <Button onClick={() => {
      setEditingRule(null);
      setDialogOpen(true);
    }}>
      Add Rule
    </Button>
  ) : undefined;

  const rows = useMemo(() => rules, [rules]);

  function formatCondition(rule: AlertRule) {
    const op = OPERATOR_LABELS[rule.operator] || rule.operator;
    return `${rule.metric_name} ${op} ${rule.threshold}`;
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="Alert Rules"
        description={description}
        action={
          isAdmin ? (
            <Button
              onClick={() => {
                setEditingRule(null);
                setDialogOpen(true);
              }}
            >
              Add Rule
            </Button>
          ) : undefined
        }
      />

      {error ? (
        <div className="text-destructive">
          Failed to load alert rules: {(error as Error).message}
        </div>
      ) : isLoading ? (
        <div className="space-y-2">
          {[1, 2, 3, 4, 5].map((i) => (
            <Skeleton key={i} className="h-12 w-full" />
          ))}
        </div>
      ) : rows.length === 0 ? (
        <EmptyState
          title="No alert rules"
          description="Create rules to trigger threshold alerts."
          icon={<ShieldAlert className="h-12 w-12" />}
          action={emptyAction}
        />
      ) : (
        <div className="rounded-md border border-border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Name</TableHead>
                <TableHead>Condition</TableHead>
                <TableHead>Severity</TableHead>
                <TableHead>Enabled</TableHead>
                <TableHead className="text-right">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {rows.map((rule) => (
                <TableRow key={rule.rule_id}>
                  <TableCell className="font-medium">{rule.name}</TableCell>
                  <TableCell className="font-mono text-sm">
                    {formatCondition(rule)}
                  </TableCell>
                  <TableCell>
                    <SeverityBadge severity={rule.severity} />
                  </TableCell>
                  <TableCell>
                    <Switch
                      checked={rule.enabled}
                      onCheckedChange={(checked) => {
                        if (!isAdmin) return;
                        updateRule.mutate({
                          ruleId: String(rule.rule_id),
                          data: { enabled: checked },
                        });
                      }}
                      disabled={!isAdmin || updateRule.isPending}
                    />
                  </TableCell>
                  <TableCell className="text-right">
                    {isAdmin ? (
                      <div className="flex justify-end gap-2">
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => {
                            setEditingRule(rule);
                            setDialogOpen(true);
                          }}
                        >
                          Edit
                        </Button>
                        <Button
                          variant="destructive"
                          size="sm"
                          onClick={() => setDeletingRule(rule)}
                        >
                          Delete
                        </Button>
                      </div>
                    ) : (
                      <span className="text-xs text-muted-foreground">View only</span>
                    )}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
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
