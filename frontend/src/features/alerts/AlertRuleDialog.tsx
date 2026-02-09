import { useEffect, useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Switch } from "@/components/ui/switch";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import {
  useCreateAlertRule,
  useUpdateAlertRule,
} from "@/hooks/use-alert-rules";
import type {
  AlertRule,
  AlertRuleCreate,
  AlertRuleUpdate,
  MetricReference,
} from "@/services/api/types";
import { ApiError } from "@/services/api/client";
import { fetchMetricReference } from "@/services/api/alert-rules";

type OperatorValue = "GT" | "LT" | "GTE" | "LTE";

interface AlertRuleDialogProps {
  open: boolean;
  onClose: () => void;
  rule?: AlertRule | null;
}

function formatError(error: unknown): string {
  if (!error) return "";
  if (error instanceof ApiError) {
    if (typeof error.body === "string") return error.body;
    if (error.body && typeof error.body === "object") {
      const detail = (error.body as { detail?: string }).detail;
      if (detail) return detail;
    }
    return error.message;
  }
  if (error instanceof Error) return error.message;
  return "Unknown error";
}

export function AlertRuleDialog({ open, onClose, rule }: AlertRuleDialogProps) {
  const isEditing = !!rule;
  const createMutation = useCreateAlertRule();
  const updateMutation = useUpdateAlertRule();
  const { data: metricReference, isLoading: metricsLoading } = useQuery({
    queryKey: ["metric-reference"],
    queryFn: fetchMetricReference,
    enabled: open,
  });

  const [name, setName] = useState("");
  const [metricName, setMetricName] = useState("");
  const [operator, setOperator] = useState<OperatorValue>("GT");
  const [threshold, setThreshold] = useState("");
  const [severity, setSeverity] = useState("3");
  const [description, setDescription] = useState("");
  const [enabled, setEnabled] = useState(true);

  useEffect(() => {
    if (!open) return;
    if (rule) {
      setName(rule.name);
      setMetricName(rule.metric_name);
      setOperator(rule.operator as OperatorValue);
      setThreshold(String(rule.threshold));
      setSeverity(String(rule.severity ?? 3));
      setDescription(rule.description ?? "");
      setEnabled(rule.enabled);
    } else {
      setName("");
      setMetricName("");
      setOperator("GT");
      setThreshold("");
      setSeverity("3");
      setDescription("");
      setEnabled(true);
    }
  }, [open, rule]);

  const errorMessage = useMemo(() => {
    return formatError(createMutation.error || updateMutation.error);
  }, [createMutation.error, updateMutation.error]);

  const metricOptions = useMemo<MetricReference[]>(() => metricReference ?? [], [metricReference]);
  const selectedMetric = useMemo(
    () => metricOptions.find((metric) => metric.name === metricName),
    [metricName, metricOptions]
  );
  const metricDetailParts = useMemo(() => {
    if (!selectedMetric) return [];
    return [
      selectedMetric.description,
      selectedMetric.unit,
      selectedMetric.range,
      selectedMetric.type,
    ].filter(Boolean) as string[];
  }, [selectedMetric]);

  const isSaving = createMutation.isPending || updateMutation.isPending;

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!metricName.trim()) return;
    const thresholdValue = Number(threshold);
    if (Number.isNaN(thresholdValue)) return;
    const normalizedDescription = description.trim() || null;
    const severityValue = Number(severity);

    if (!isEditing) {
      const payload: AlertRuleCreate = {
        name,
        metric_name: metricName,
        operator,
        threshold: thresholdValue,
        severity: Number.isNaN(severityValue) ? undefined : severityValue,
        description: normalizedDescription,
        enabled,
      };
      await createMutation.mutateAsync(payload);
      onClose();
      return;
    }

    if (!rule) return;
    const updates: AlertRuleUpdate = {};
    if (name !== rule.name) updates.name = name;
    if (metricName !== rule.metric_name) updates.metric_name = metricName;
    if (operator !== rule.operator) updates.operator = operator;
    if (thresholdValue !== rule.threshold) updates.threshold = thresholdValue;
    if (severityValue !== rule.severity) updates.severity = severityValue;
    if (normalizedDescription !== (rule.description ?? null)) {
      updates.description = normalizedDescription;
    }
    if (enabled !== rule.enabled) updates.enabled = enabled;

    if (Object.keys(updates).length === 0) {
      onClose();
      return;
    }

    await updateMutation.mutateAsync({ ruleId: String(rule.rule_id), data: updates });
    onClose();
  }

  return (
    <Dialog open={open} onOpenChange={(nextOpen) => !nextOpen && onClose()}>
      <DialogContent className="max-h-[85vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>{isEditing ? "Edit Alert Rule" : "Create Alert Rule"}</DialogTitle>
          <DialogDescription>
            Define threshold conditions that trigger alerts.
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="grid gap-2">
            <Label htmlFor="rule-name">Name</Label>
            <Input
              id="rule-name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              required
              minLength={1}
              maxLength={100}
              placeholder="Battery Low"
            />
          </div>

          <div className="grid gap-2">
            <Label htmlFor="metric-name">Metric Name</Label>
            <div className="flex items-center gap-2">
              <Select value={metricName || undefined} onValueChange={setMetricName}>
                <SelectTrigger id="metric-name" className="w-full" disabled={metricsLoading}>
                  <SelectValue placeholder={metricsLoading ? "Loading metrics..." : "Select metric"} />
                </SelectTrigger>
                <SelectContent>
                  {metricOptions.map((metric) => (
                    <SelectItem key={metric.name} value={metric.name}>
                      {metric.name}
                      {metric.description ? ` — ${metric.description}` : ""}
                    </SelectItem>
                  ))}
                  {metricName && !selectedMetric && (
                    <SelectItem value={metricName}>Custom: {metricName}</SelectItem>
                  )}
                </SelectContent>
              </Select>
              {selectedMetric && (
                <TooltipProvider>
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <span className="inline-flex h-8 w-8 items-center justify-center rounded-md border border-border text-xs text-muted-foreground">
                        i
                      </span>
                    </TooltipTrigger>
                    <TooltipContent side="right">
                      <div className="space-y-1">
                        <div className="font-medium">{selectedMetric.name}</div>
                        {metricDetailParts.length > 0 ? (
                          <div>{metricDetailParts.join(" · ")}</div>
                        ) : (
                          <div>No metadata available.</div>
                        )}
                      </div>
                    </TooltipContent>
                  </Tooltip>
                </TooltipProvider>
              )}
            </div>
            <p className="text-xs text-muted-foreground">
              {metricsLoading
                ? "Loading metric reference..."
                : metricOptions.length === 0
                ? "No metrics found. Metrics will appear after devices send telemetry."
                : "Select a metric to see details."}
            </p>
          </div>

          <div className="grid gap-2">
            <Label>Operator</Label>
            <Select value={operator} onValueChange={(v) => setOperator(v as OperatorValue)}>
              <SelectTrigger className="w-full">
                <SelectValue placeholder="Select operator" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="GT">{"\u003e"} (GT)</SelectItem>
                <SelectItem value="LT">{"\u003c"} (LT)</SelectItem>
                <SelectItem value="GTE">{"\u2265"} (GTE)</SelectItem>
                <SelectItem value="LTE">{"\u2264"} (LTE)</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div className="grid gap-2">
            <Label htmlFor="threshold">Threshold</Label>
            <Input
              id="threshold"
              type="number"
              value={threshold}
              onChange={(e) => setThreshold(e.target.value)}
              required
              step="any"
            />
          </div>

          <div className="grid gap-2">
            <Label>Severity</Label>
            <Select value={severity} onValueChange={setSeverity}>
              <SelectTrigger className="w-full">
                <SelectValue placeholder="Select severity" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="1">1 (Info)</SelectItem>
                <SelectItem value="2">2 (Low)</SelectItem>
                <SelectItem value="3">3 (Medium)</SelectItem>
                <SelectItem value="4">4 (High)</SelectItem>
                <SelectItem value="5">5 (Critical)</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div className="grid gap-2">
            <Label htmlFor="description">Description</Label>
            <Textarea
              id="description"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Optional context for this rule"
            />
          </div>

          <div className="flex items-center justify-between rounded-md border border-border p-3">
            <div>
              <Label className="text-sm">Enabled</Label>
              <p className="text-xs text-muted-foreground">
                Alerts will trigger when enabled.
              </p>
            </div>
            <Switch checked={enabled} onCheckedChange={setEnabled} />
          </div>

          {errorMessage && (
            <div className="text-sm text-destructive">
              {errorMessage}
            </div>
          )}

          <DialogFooter>
            <Button type="button" variant="outline" onClick={onClose}>
              Cancel
            </Button>
            <Button type="submit" disabled={isSaving}>
              {isSaving ? "Saving..." : isEditing ? "Save Changes" : "Create Rule"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
