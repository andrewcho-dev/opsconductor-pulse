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
  SelectGroup,
  SelectItem,
  SelectLabel,
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
import { fetchDeviceGroups, type DeviceGroup } from "@/services/api/devices";
import type {
  AlertRule,
  AlertRuleCreate,
  AlertRuleUpdate,
  AnomalyConditions,
  NormalizedMetricReference,
  RawMetricReference,
  RuleCondition,
  TelemetryGapConditions,
} from "@/services/api/types";
import { ApiError } from "@/services/api/client";
import { fetchMetricReference } from "@/services/api/metrics";
import {
  fetchAlertRuleTemplates,
  type AlertRuleTemplate,
} from "@/services/api/alert-rules";

type OperatorValue = "GT" | "LT" | "GTE" | "LTE";
type RuleMode = "simple" | "multi" | "anomaly" | "gap";

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
  const { data: templates = [] } = useQuery({
    queryKey: ["alert-rule-templates"],
    queryFn: () => fetchAlertRuleTemplates(),
    enabled: open && !isEditing,
  });
  const { data: deviceGroupsResponse } = useQuery({
    queryKey: ["device-groups"],
    queryFn: fetchDeviceGroups,
    enabled: open,
  });

  const [name, setName] = useState("");
  const [metricName, setMetricName] = useState("");
  const [operator, setOperator] = useState<OperatorValue>("GT");
  const [threshold, setThreshold] = useState("");
  const [severity, setSeverity] = useState("3");
  const [durationSeconds, setDurationSeconds] = useState("0");
  const [description, setDescription] = useState("");
  const [enabled, setEnabled] = useState(true);
  const [selectedTemplateId, setSelectedTemplateId] = useState<string>("");
  const [ruleMode, setRuleMode] = useState<RuleMode>("simple");
  const [combinator, setCombinator] = useState<"AND" | "OR">("AND");
  const [multiConditions, setMultiConditions] = useState<RuleCondition[]>([
    { metric_name: "", operator: "GT", threshold: 0 },
  ]);
  const [anomalyMetricName, setAnomalyMetricName] = useState("");
  const [anomalyWindowMinutes, setAnomalyWindowMinutes] = useState("60");
  const [anomalyZThreshold, setAnomalyZThreshold] = useState("3");
  const [anomalyMinSamples, setAnomalyMinSamples] = useState("10");
  const [gapMetricName, setGapMetricName] = useState("");
  const [gapMinutes, setGapMinutes] = useState("10");
  const [selectedGroupIds, setSelectedGroupIds] = useState<string[]>([]);

  useEffect(() => {
    if (!open) return;
    if (rule) {
      setName(rule.name);
      setMetricName(rule.metric_name);
      setOperator(rule.operator as OperatorValue);
      setThreshold(String(rule.threshold));
      setSeverity(String(rule.severity ?? 3));
      setDurationSeconds(String(rule.duration_seconds ?? 0));
      setDescription(rule.description ?? "");
      setEnabled(rule.enabled);
      setSelectedGroupIds(rule.group_ids ?? []);
      if (rule.rule_type === "anomaly" && rule.anomaly_conditions) {
        setRuleMode("anomaly");
        setAnomalyMetricName(rule.anomaly_conditions.metric_name);
        setAnomalyWindowMinutes(String(rule.anomaly_conditions.window_minutes));
        setAnomalyZThreshold(String(rule.anomaly_conditions.z_threshold));
        setAnomalyMinSamples(String(rule.anomaly_conditions.min_samples));
        setCombinator("AND");
        setMultiConditions([{ metric_name: "", operator: "GT", threshold: 0 }]);
      } else if (rule.rule_type === "telemetry_gap" && rule.gap_conditions) {
        setRuleMode("gap");
        setGapMetricName(rule.gap_conditions.metric_name);
        setGapMinutes(String(rule.gap_conditions.gap_minutes));
        setCombinator("AND");
        setMultiConditions([{ metric_name: "", operator: "GT", threshold: 0 }]);
      } else if (rule.conditions?.conditions?.length) {
        setRuleMode("multi");
        setCombinator(rule.conditions.combinator);
        setMultiConditions(rule.conditions.conditions);
      } else {
        setRuleMode("simple");
        setCombinator("AND");
        setMultiConditions([{ metric_name: "", operator: "GT", threshold: 0 }]);
        setAnomalyMetricName("");
        setAnomalyWindowMinutes("60");
        setAnomalyZThreshold("3");
        setAnomalyMinSamples("10");
        setGapMetricName("");
        setGapMinutes("10");
      }
    } else {
      setName("");
      setMetricName("");
      setOperator("GT");
      setThreshold("");
      setSeverity("3");
      setDurationSeconds("0");
      setDescription("");
      setEnabled(true);
      setSelectedTemplateId("");
      setRuleMode("simple");
      setCombinator("AND");
      setMultiConditions([{ metric_name: "", operator: "GT", threshold: 0 }]);
      setAnomalyMetricName("");
      setAnomalyWindowMinutes("60");
      setAnomalyZThreshold("3");
      setAnomalyMinSamples("10");
      setGapMetricName("");
      setGapMinutes("10");
      setSelectedGroupIds([]);
    }
  }, [open, rule]);

  const errorMessage = useMemo(() => {
    return formatError(createMutation.error || updateMutation.error);
  }, [createMutation.error, updateMutation.error]);

  const normalizedMetrics = useMemo<NormalizedMetricReference[]>(
    () =>
      Array.isArray(metricReference?.normalized_metrics)
        ? metricReference.normalized_metrics
        : [],
    [metricReference]
  );
  const rawMetrics = useMemo<RawMetricReference[]>(
    () =>
      Array.isArray(metricReference?.raw_metrics) ? metricReference.raw_metrics : [],
    [metricReference]
  );
  const selectedNormalized = useMemo(
    () => normalizedMetrics.find((metric) => metric.name === metricName),
    [metricName, normalizedMetrics]
  );
  const selectedRaw = useMemo(
    () => rawMetrics.find((metric) => metric.name === metricName),
    [metricName, rawMetrics]
  );

  const normalizedRange = useMemo(() => {
    if (!selectedNormalized) return null;
    if (selectedNormalized.expected_min == null && selectedNormalized.expected_max == null) {
      return null;
    }
    const min = selectedNormalized.expected_min ?? "";
    const max = selectedNormalized.expected_max ?? "";
    return `${min}-${max}`;
  }, [selectedNormalized]);

  const isSaving = createMutation.isPending || updateMutation.isPending;

  function applyTemplate(template: AlertRuleTemplate) {
    setSelectedTemplateId(template.template_id);
    setName(template.name);
    setMetricName(template.metric_name);
    setOperator(template.operator);
    setThreshold(String(template.threshold));
    setSeverity(String(template.severity));
    setDurationSeconds(String(template.duration_seconds));
    setDescription(template.description ?? "");
    setRuleMode("simple");
  }

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (ruleMode === "simple" && !metricName.trim()) return;
    if (ruleMode === "anomaly" && !anomalyMetricName.trim()) return;
    if (ruleMode === "gap" && !gapMetricName.trim()) return;
    const thresholdValue = Number(threshold);
    if (ruleMode === "simple" && Number.isNaN(thresholdValue)) return;
    const anomalyConditions: AnomalyConditions = {
      metric_name: anomalyMetricName.trim(),
      window_minutes: Number(anomalyWindowMinutes),
      z_threshold: Number(anomalyZThreshold),
      min_samples: Number(anomalyMinSamples),
    };
    const gapConditions: TelemetryGapConditions = {
      metric_name: gapMetricName.trim(),
      gap_minutes: Number(gapMinutes),
    };
    if (
      ruleMode === "anomaly" &&
      (
        Number.isNaN(anomalyConditions.window_minutes) ||
        Number.isNaN(anomalyConditions.z_threshold) ||
        Number.isNaN(anomalyConditions.min_samples)
      )
    ) {
      return;
    }
    if (ruleMode === "gap" && Number.isNaN(gapConditions.gap_minutes)) {
      return;
    }
    const normalizedDescription = description.trim() || null;
    const severityValue = Number(severity);
    const durationValue = Number(durationSeconds);
    if (!Number.isInteger(durationValue) || durationValue < 0) return;

    if (!isEditing) {
      const payload: AlertRuleCreate = {
        name,
        severity: Number.isNaN(severityValue) ? undefined : severityValue,
        duration_seconds: durationValue,
        description: normalizedDescription,
        enabled,
        group_ids: selectedGroupIds.length ? selectedGroupIds : null,
      };
      if (ruleMode === "anomaly") {
        payload.rule_type = "anomaly";
        payload.anomaly_conditions = anomalyConditions;
      } else if (ruleMode === "gap") {
        payload.rule_type = "telemetry_gap";
        payload.gap_conditions = gapConditions;
      } else if (ruleMode === "multi") {
        payload.rule_type = "threshold";
        payload.conditions = {
          combinator,
          conditions: multiConditions
            .filter((c) => c.metric_name.trim())
            .map((c) => ({
              metric_name: c.metric_name.trim(),
              operator: c.operator,
              threshold: Number(c.threshold),
            })),
        };
      } else {
        payload.rule_type = "threshold";
        payload.metric_name = metricName;
        payload.operator = operator;
        payload.threshold = thresholdValue;
      }
      await createMutation.mutateAsync(payload);
      onClose();
      return;
    }

    if (!rule) return;
    const updates: AlertRuleUpdate = {};
    if (name !== rule.name) updates.name = name;
    if (ruleMode === "anomaly") {
      updates.rule_type = "anomaly";
      updates.anomaly_conditions = anomalyConditions;
      updates.gap_conditions = null;
      updates.conditions = null;
      updates.metric_name = anomalyMetricName.trim();
      updates.operator = "GT";
      updates.threshold = anomalyConditions.z_threshold;
    } else if (ruleMode === "gap") {
      updates.rule_type = "telemetry_gap";
      updates.gap_conditions = gapConditions;
      updates.anomaly_conditions = null;
      updates.conditions = null;
      updates.metric_name = gapConditions.metric_name;
      updates.operator = "GT";
      updates.threshold = gapConditions.gap_minutes;
    } else if (ruleMode === "multi") {
      updates.rule_type = "threshold";
      updates.conditions = {
        combinator,
        conditions: multiConditions
          .filter((c) => c.metric_name.trim())
          .map((c) => ({
            metric_name: c.metric_name.trim(),
            operator: c.operator,
            threshold: Number(c.threshold),
          })),
      };
      updates.anomaly_conditions = null;
      updates.gap_conditions = null;
    } else {
      updates.rule_type = "threshold";
      if (metricName !== rule.metric_name) updates.metric_name = metricName;
      if (operator !== rule.operator) updates.operator = operator;
      if (thresholdValue !== rule.threshold) updates.threshold = thresholdValue;
      updates.conditions = null;
      updates.anomaly_conditions = null;
      updates.gap_conditions = null;
    }
    if (severityValue !== rule.severity) updates.severity = severityValue;
    if (durationValue !== (rule.duration_seconds ?? 0)) {
      updates.duration_seconds = durationValue;
    }
    if (normalizedDescription !== (rule.description ?? null)) {
      updates.description = normalizedDescription;
    }
    if (enabled !== rule.enabled) updates.enabled = enabled;
    if (JSON.stringify(selectedGroupIds) !== JSON.stringify(rule.group_ids ?? [])) {
      updates.group_ids = selectedGroupIds;
    }

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
          {!isEditing && templates.length > 0 && (
            <div className="grid gap-2">
              <Label>Load from Template</Label>
              <Select
                value={selectedTemplateId || undefined}
                onValueChange={(value) => {
                  const template = templates.find((tmpl) => tmpl.template_id === value);
                  if (template) applyTemplate(template);
                }}
              >
                <SelectTrigger className="w-full">
                  <SelectValue placeholder="Select template" />
                </SelectTrigger>
                <SelectContent>
                  {Array.from(new Set(templates.map((tmpl) => tmpl.device_type))).map((deviceType) => (
                    <SelectGroup key={deviceType}>
                      <SelectLabel>{deviceType}</SelectLabel>
                      {templates
                        .filter((tmpl) => tmpl.device_type === deviceType)
                        .map((tmpl) => (
                          <SelectItem key={tmpl.template_id} value={tmpl.template_id}>
                            {tmpl.name}
                          </SelectItem>
                        ))}
                    </SelectGroup>
                  ))}
                </SelectContent>
              </Select>
            </div>
          )}

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
            <Label>Rule Mode</Label>
            <div className="flex gap-2">
              <Button
                type="button"
                variant={ruleMode === "simple" ? "default" : "outline"}
                onClick={() => setRuleMode("simple")}
              >
                Simple Rule
              </Button>
              <Button
                type="button"
                variant={ruleMode === "multi" ? "default" : "outline"}
                onClick={() => setRuleMode("multi")}
              >
                Multi-Condition Rule
              </Button>
              <Button
                type="button"
                variant={ruleMode === "anomaly" ? "default" : "outline"}
                onClick={() => setRuleMode("anomaly")}
              >
                Anomaly Detection
              </Button>
              <Button
                type="button"
                variant={ruleMode === "gap" ? "default" : "outline"}
                onClick={() => setRuleMode("gap")}
              >
                Data Gap
              </Button>
            </div>
          </div>

          {ruleMode === "simple" ? (
            <>
              <div className="grid gap-2">
                <Label htmlFor="metric-name">Metric Name</Label>
                <div className="flex items-center gap-2">
                  <Select value={metricName || undefined} onValueChange={setMetricName}>
                    <SelectTrigger id="metric-name" className="w-full" disabled={metricsLoading}>
                      <SelectValue placeholder={metricsLoading ? "Loading metrics..." : "Select metric"} />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectGroup>
                        <SelectLabel>Normalized</SelectLabel>
                        {normalizedMetrics.length === 0 ? (
                          <SelectItem value="__no_normalized" disabled>
                            No normalized metrics
                          </SelectItem>
                        ) : (
                          normalizedMetrics.map((metric) => (
                            <SelectItem key={metric.name} value={metric.name}>
                              {metric.name}
                              {metric.display_unit ? ` (${metric.display_unit})` : ""}
                            </SelectItem>
                          ))
                        )}
                      </SelectGroup>
                      <SelectGroup>
                        <SelectLabel>Raw</SelectLabel>
                        {rawMetrics.length === 0 ? (
                          <SelectItem value="__no_raw" disabled>
                            No raw metrics
                          </SelectItem>
                        ) : (
                          rawMetrics.map((metric) => (
                            <SelectItem key={metric.name} value={metric.name}>
                              {metric.name}
                              {metric.mapped_to ? ` → ${metric.mapped_to}` : ""}
                            </SelectItem>
                          ))
                        )}
                      </SelectGroup>
                    </SelectContent>
                  </Select>
                  {(selectedNormalized || selectedRaw) && (
                    <TooltipProvider>
                      <Tooltip>
                        <TooltipTrigger asChild>
                          <span className="inline-flex h-8 w-8 items-center justify-center rounded-md border border-border text-xs text-muted-foreground">
                            i
                          </span>
                        </TooltipTrigger>
                        <TooltipContent side="right">
                          <div className="space-y-1">
                            <div className="font-medium">
                              {selectedNormalized?.name || selectedRaw?.name}
                            </div>
                            {selectedNormalized ? (
                              <div className="space-y-1">
                                {selectedNormalized.description && (
                                  <div>{selectedNormalized.description}</div>
                                )}
                                {selectedNormalized.display_unit && (
                                  <div>Unit: {selectedNormalized.display_unit}</div>
                                )}
                                {normalizedRange && <div>Range: {normalizedRange}</div>}
                                {selectedNormalized.mapped_from.length > 0 ? (
                                  <div>
                                    Includes: {selectedNormalized.mapped_from.join(", ")}
                                  </div>
                                ) : (
                                  <div>No raw metrics mapped.</div>
                                )}
                              </div>
                            ) : (
                              <div>
                                {selectedRaw?.mapped_to
                                  ? `Mapped to: ${selectedRaw.mapped_to}`
                                  : "Unmapped raw metric"}
                              </div>
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
                    : normalizedMetrics.length === 0 && rawMetrics.length === 0
                    ? "No metrics found. Metrics will appear after devices send telemetry."
                    : selectedNormalized
                    ? `Includes: ${selectedNormalized.mapped_from.join(", ") || "none"}`
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
            </>
          ) : ruleMode === "multi" ? (
            <div className="space-y-3 rounded-md border border-border p-3">
              <div className="flex items-center gap-2">
                <Label>Combinator</Label>
                <Button
                  type="button"
                  variant={combinator === "AND" ? "default" : "outline"}
                  size="sm"
                  onClick={() => setCombinator("AND")}
                >
                  AND
                </Button>
                <Button
                  type="button"
                  variant={combinator === "OR" ? "default" : "outline"}
                  size="sm"
                  onClick={() => setCombinator("OR")}
                >
                  OR
                </Button>
              </div>
              {multiConditions.map((condition, idx) => (
                <div key={idx} className="grid gap-2 md:grid-cols-[1fr_140px_160px_auto]">
                  <Input
                    placeholder="metric_name"
                    value={condition.metric_name}
                    onChange={(e) =>
                      setMultiConditions((prev) =>
                        prev.map((c, i) =>
                          i === idx ? { ...c, metric_name: e.target.value } : c
                        )
                      )
                    }
                  />
                  <Select
                    value={condition.operator}
                    onValueChange={(v) =>
                      setMultiConditions((prev) =>
                        prev.map((c, i) =>
                          i === idx ? { ...c, operator: v as OperatorValue } : c
                        )
                      )
                    }
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="GT">GT</SelectItem>
                      <SelectItem value="LT">LT</SelectItem>
                      <SelectItem value="GTE">GTE</SelectItem>
                      <SelectItem value="LTE">LTE</SelectItem>
                    </SelectContent>
                  </Select>
                  <Input
                    type="number"
                    step="any"
                    value={condition.threshold}
                    onChange={(e) =>
                      setMultiConditions((prev) =>
                        prev.map((c, i) =>
                          i === idx
                            ? { ...c, threshold: Number(e.target.value || 0) }
                            : c
                        )
                      )
                    }
                  />
                  <Button
                    type="button"
                    variant="outline"
                    disabled={multiConditions.length <= 1}
                    onClick={() =>
                      setMultiConditions((prev) => prev.filter((_, i) => i !== idx))
                    }
                  >
                    Remove
                  </Button>
                </div>
              ))}
              <Button
                type="button"
                variant="outline"
                disabled={multiConditions.length >= 10}
                onClick={() =>
                  setMultiConditions((prev) => [
                    ...prev,
                    { metric_name: "", operator: "GT", threshold: 0 },
                  ])
                }
              >
                Add Condition
              </Button>
            </div>
          ) : ruleMode === "anomaly" ? (
            <div className="space-y-3 rounded-md border border-border p-3">
              <div className="grid gap-2">
                <Label htmlFor="anomaly-metric-name">Metric Name</Label>
                <Input
                  id="anomaly-metric-name"
                  value={anomalyMetricName}
                  onChange={(e) => setAnomalyMetricName(e.target.value)}
                  placeholder="temperature"
                  required={ruleMode === "anomaly"}
                />
              </div>
              <div className="grid gap-2">
                <Label>Window</Label>
                <Select value={anomalyWindowMinutes} onValueChange={setAnomalyWindowMinutes}>
                  <SelectTrigger className="w-full">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="15">15 min</SelectItem>
                    <SelectItem value="30">30 min</SelectItem>
                    <SelectItem value="60">1 hour</SelectItem>
                    <SelectItem value="360">6 hours</SelectItem>
                    <SelectItem value="1440">24 hours</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="grid gap-2">
                <Label htmlFor="anomaly-z-threshold">Z-Score Threshold</Label>
                <Input
                  id="anomaly-z-threshold"
                  type="number"
                  min={1}
                  max={10}
                  step="0.1"
                  value={anomalyZThreshold}
                  onChange={(e) => setAnomalyZThreshold(e.target.value)}
                />
              </div>
              <div className="grid gap-2">
                <Label htmlFor="anomaly-min-samples">Min Samples</Label>
                <Input
                  id="anomaly-min-samples"
                  type="number"
                  min={3}
                  step={1}
                  value={anomalyMinSamples}
                  onChange={(e) => setAnomalyMinSamples(e.target.value)}
                />
              </div>
            </div>
          ) : (
            <div className="space-y-3 rounded-md border border-border p-3">
              <div className="grid gap-2">
                <Label htmlFor="gap-metric-name">Metric Name</Label>
                <Input
                  id="gap-metric-name"
                  value={gapMetricName}
                  onChange={(e) => setGapMetricName(e.target.value)}
                  placeholder="temperature"
                  required={ruleMode === "gap"}
                />
              </div>
              <div className="grid gap-2">
                <Label htmlFor="gap-minutes">Gap Threshold (minutes)</Label>
                <Input
                  id="gap-minutes"
                  type="number"
                  min={1}
                  step={1}
                  value={gapMinutes}
                  onChange={(e) => setGapMinutes(e.target.value)}
                />
                <p className="text-xs text-muted-foreground">
                  Alert if no {gapMetricName || "metric"} data for {gapMinutes || "0"} minutes.
                </p>
              </div>
            </div>
          )}

          <div className="grid gap-2">
            <Label>Device Groups</Label>
            <div className="max-h-40 space-y-2 overflow-auto rounded-md border border-border p-2">
              {(deviceGroupsResponse?.groups ?? []).length === 0 ? (
                <p className="text-xs text-muted-foreground">No device groups yet.</p>
              ) : (
                (deviceGroupsResponse?.groups ?? []).map((group: DeviceGroup) => (
                  <label
                    key={group.group_id}
                    className="flex items-center justify-between gap-2 text-sm"
                  >
                    <span>{group.name}</span>
                    <input
                      type="checkbox"
                      checked={selectedGroupIds.includes(group.group_id)}
                      onChange={(e) => {
                        if (e.target.checked) {
                          setSelectedGroupIds((prev) => [...new Set([...prev, group.group_id])]);
                        } else {
                          setSelectedGroupIds((prev) => prev.filter((id) => id !== group.group_id));
                        }
                      }}
                    />
                  </label>
                ))
              )}
            </div>
          </div>

          <div className="grid gap-2">
            <Label htmlFor="duration-seconds">Duration (seconds)</Label>
            <Input
              id="duration-seconds"
              type="number"
              min={0}
              step={1}
              value={durationSeconds}
              onChange={(e) => setDurationSeconds(e.target.value)}
            />
            <p className="text-xs text-muted-foreground">
              0 = alert immediately. Set to 60+ to require sustained condition.
            </p>
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
