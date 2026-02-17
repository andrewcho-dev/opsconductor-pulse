import { useEffect, useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { z } from "zod";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { useFormDirtyGuard } from "@/hooks/use-form-dirty-guard";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription as AlertDialogDescriptionText,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Switch } from "@/components/ui/switch";
import { Button } from "@/components/ui/button";
import {
  Form,
  FormControl,
  FormDescription,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
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
  MatchMode,
  NormalizedMetricReference,
  RawMetricReference,
  RuleCondition,
  RuleOperator,
} from "@/services/api/types";
import { ApiError } from "@/services/api/client";
import { fetchMetricReference } from "@/services/api/metrics";
import {
  fetchAlertRuleTemplates,
  type AlertRuleTemplate,
} from "@/services/api/alert-rules";
import { ConditionRow } from "./ConditionRow";

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

const ruleOperators = ["GT", "GTE", "LT", "LTE"] as const;
const matchModes = ["all", "any"] as const;
const windowAggregations = ["avg", "min", "max", "count", "sum"] as const;

const requiredNumber = (message = "Must be a number") =>
  z
    .union([z.number(), z.string()])
    .transform((v) => {
      if (typeof v === "number") return v;
      if (v.trim() === "") return Number.NaN;
      return Number(v);
    })
    .refine((n) => Number.isFinite(n), { message });

const requiredInt = (min: number, message = "Must be a number") =>
  requiredNumber(message)
    .transform((n) => Math.trunc(n))
    .refine((n) => Number.isInteger(n) && n >= min, { message });

const optionalMinutes = z
  .union([z.number(), z.string(), z.null(), z.undefined()])
  .transform((v) => {
    if (v == null) return null;
    if (typeof v === "number") return Number.isFinite(v) ? Math.trunc(v) : Number.NaN;
    if (v.trim() === "") return null;
    const n = Number(v);
    return Number.isFinite(n) ? Math.trunc(n) : Number.NaN;
  })
  .refine((v) => v === null || (Number.isInteger(v) && v >= 1), {
    message: "Must be at least 1",
  });

const conditionSchema = z.object({
  metric_name: z.string().min(1, "Metric is required"),
  operator: z.enum(ruleOperators),
  threshold: requiredNumber(),
  duration_minutes: optionalMinutes,
});

const commonSchema = z.object({
  name: z.string().min(3, "Name must be at least 3 characters").max(100),
  severity: requiredInt(1, "Severity must be a number").refine((n) => n >= 1 && n <= 5, {
    message: "Severity must be between 1 and 5",
  }),
  duration_minutes: optionalMinutes,
  description: z.string().optional().default(""),
  enabled: z.boolean().default(true),
  group_ids: z.array(z.string()).default([]),
  device_group_id: z.string().optional().default(""),
});

const alertRuleSchema = z.discriminatedUnion("ruleMode", [
  commonSchema.extend({
    ruleMode: z.literal("simple"),
    metric_name: z.string().min(1, "Metric name is required"),
    operator: z.enum(ruleOperators),
    threshold: requiredNumber(),
  }),
  commonSchema.extend({
    ruleMode: z.literal("multi"),
    conditions: z.array(conditionSchema).min(1, "At least one condition required").max(10),
    match_mode: z.enum(matchModes).default("all"),
  }),
  commonSchema.extend({
    ruleMode: z.literal("anomaly"),
    anomaly_metric_name: z.string().min(1, "Metric name is required"),
    anomaly_window_minutes: requiredInt(1, "Window must be a number"),
    anomaly_z_threshold: requiredNumber("Z-threshold must be a number").refine((n) => n >= 1, {
      message: "Z-threshold must be at least 1",
    }),
    anomaly_min_samples: requiredInt(3, "Min samples must be a number"),
  }),
  commonSchema.extend({
    ruleMode: z.literal("gap"),
    gap_metric_name: z.string().min(1, "Metric name is required"),
    gap_minutes: requiredInt(1, "Gap minutes must be a number"),
  }),
  commonSchema.extend({
    ruleMode: z.literal("window"),
    metric_name: z.string().min(1, "Metric name is required"),
    operator: z.enum(ruleOperators),
    threshold: requiredNumber(),
    window_aggregation: z.enum(windowAggregations).default("avg"),
    window_seconds: requiredInt(1, "Window must be a number"),
  }),
]);

// Superset type for RHF field names (union keyof collapses otherwise).
type AlertRuleFormValues = {
  ruleMode: "simple" | "multi" | "anomaly" | "gap" | "window";
  name: string;
  severity: number;
  duration_minutes: number | null;
  description: string;
  enabled: boolean;
  group_ids: string[];
  device_group_id: string;
  metric_name?: string;
  operator?: RuleOperator;
  threshold?: number;
  match_mode?: MatchMode;
  conditions?: Array<{
    metric_name: string;
    operator: RuleOperator;
    threshold: number;
    duration_minutes: number | null;
  }>;
  anomaly_metric_name?: string;
  anomaly_window_minutes?: number;
  anomaly_z_threshold?: number;
  anomaly_min_samples?: number;
  gap_metric_name?: string;
  gap_minutes?: number;
  window_aggregation?: (typeof windowAggregations)[number];
  window_seconds?: number;
};

const defaultValues: AlertRuleFormValues = {
  ruleMode: "simple",
  name: "",
  metric_name: "",
  operator: "GT",
  threshold: 0,
  severity: 3,
  duration_minutes: null,
  description: "",
  enabled: true,
  group_ids: [],
  device_group_id: "",
};

function mapRuleToFormValues(rule: AlertRule): AlertRuleFormValues {
  const durationMinutes =
    rule.duration_minutes ??
    ((rule.duration_seconds ?? 0) > 0 ? Math.ceil((rule.duration_seconds ?? 0) / 60) : null);

  const base: AlertRuleFormValues = {
    ...defaultValues,
    name: rule.name ?? "",
    severity: rule.severity ?? 3,
    duration_minutes: durationMinutes,
    description: rule.description ?? "",
    enabled: Boolean(rule.enabled),
    group_ids: rule.group_ids ?? [],
    device_group_id: rule.device_group_id ?? "",
  };

  if (rule.rule_type === "anomaly" && rule.anomaly_conditions) {
    return {
      ...base,
      ruleMode: "anomaly",
      anomaly_metric_name: rule.anomaly_conditions.metric_name,
      anomaly_window_minutes: rule.anomaly_conditions.window_minutes,
      anomaly_z_threshold: rule.anomaly_conditions.z_threshold,
      anomaly_min_samples: rule.anomaly_conditions.min_samples,
    };
  }

  if (rule.rule_type === "telemetry_gap" && rule.gap_conditions) {
    return {
      ...base,
      ruleMode: "gap",
      gap_metric_name: rule.gap_conditions.metric_name,
      gap_minutes: rule.gap_conditions.gap_minutes,
    };
  }

  if (rule.rule_type === "window") {
    return {
      ...base,
      ruleMode: "window",
      metric_name: rule.metric_name ?? "",
      operator: rule.operator as RuleOperator,
      threshold: rule.threshold ?? 0,
      window_aggregation: rule.aggregation ?? "avg",
      window_seconds: rule.window_seconds ?? 300,
    };
  }

  if (Array.isArray(rule.conditions) && rule.conditions.length > 0) {
    return {
      ...base,
      ruleMode: "multi",
      match_mode: (rule.match_mode ?? "all") as MatchMode,
      conditions: rule.conditions.map((c) => ({
        metric_name: c.metric_name ?? "",
        operator: c.operator as RuleOperator,
        threshold: c.threshold ?? 0,
        duration_minutes: c.duration_minutes ?? null,
      })),
    };
  }

  return {
    ...base,
    ruleMode: "simple",
    metric_name: rule.metric_name ?? "",
    operator: rule.operator as RuleOperator,
    threshold: rule.threshold ?? 0,
  };
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

  const [selectedTemplateId, setSelectedTemplateId] = useState<string>("");

  const form = useForm<AlertRuleFormValues>({
    resolver: zodResolver(alertRuleSchema) as any,
    defaultValues,
    mode: "onSubmit",
  });

  const { handleClose, showConfirm, confirmDiscard, cancelDiscard } = useFormDirtyGuard({
    form,
    onClose,
  });

  const ruleMode = form.watch("ruleMode");
  const metricName = form.watch("metric_name") ?? "";
  const matchMode = form.watch("match_mode") ?? "all";
  const multiConditions = ruleMode === "multi" ? form.watch("conditions") ?? [] : [];
  const gapMetricName = form.watch("gap_metric_name") ?? "";
  const gapMinutes = String(form.watch("gap_minutes") ?? 10);
  const windowAggregation = form.watch("window_aggregation") ?? "avg";
  const windowSeconds = String(form.watch("window_seconds") ?? 300);

  useEffect(() => {
    if (!open) return;
    if (open && rule) {
      form.reset(mapRuleToFormValues(rule));
    } else if (open) {
      form.reset(defaultValues);
      setSelectedTemplateId("");
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
    const current = form.getValues();
    form.reset({
      ...current,
      ruleMode: "simple",
      name: template.name,
      metric_name: template.metric_name,
      operator: template.operator,
      threshold: template.threshold,
      severity: template.severity,
      duration_minutes:
        template.duration_seconds > 0 ? Math.ceil(template.duration_seconds / 60) : null,
      description: template.description ?? "",
    });
  }

  function updateCondition(index: number, updated: RuleCondition) {
    const current = form.getValues("conditions") ?? [];
    const normalized = {
      metric_name: updated.metric_name ?? "",
      operator: updated.operator as RuleOperator,
      threshold: Number(updated.threshold ?? 0),
      duration_minutes: updated.duration_minutes ?? null,
    };
    const next = current.map((c, rowIndex) => (rowIndex === index ? normalized : c));
    form.setValue("conditions", next, { shouldValidate: true, shouldDirty: true });
  }

  function removeCondition(index: number) {
    const current = form.getValues("conditions") ?? [];
    const next = current.filter((_, rowIndex) => rowIndex !== index);
    form.setValue("conditions", next.length ? next : [{ metric_name: "", operator: "GT", threshold: 0, duration_minutes: null }], {
      shouldValidate: true,
      shouldDirty: true,
    });
  }

  function addCondition() {
    const current = form.getValues("conditions") ?? [];
    form.setValue(
      "conditions",
      [...current, { metric_name: "", operator: "GT", threshold: 0, duration_minutes: null }],
      { shouldValidate: true, shouldDirty: true }
    );
  }

  const onSubmit = async (values: AlertRuleFormValues) => {
    const normalizedDescription = values.description.trim() || null;
    const durationMinutesValue = values.duration_minutes ?? null;

    if (!isEditing) {
      const payload: AlertRuleCreate = {
        name: values.name,
        severity: values.severity,
        duration_minutes: durationMinutesValue,
        duration_seconds: durationMinutesValue == null ? 0 : durationMinutesValue * 60,
        description: normalizedDescription,
        enabled: values.enabled,
        group_ids: values.group_ids.length ? values.group_ids : null,
        device_group_id: values.device_group_id || null,
      };
      if (values.ruleMode === "anomaly") {
        payload.rule_type = "anomaly";
        payload.anomaly_conditions = {
          metric_name: values.anomaly_metric_name ?? "",
          window_minutes: Number(values.anomaly_window_minutes ?? 60),
          z_threshold: Number(values.anomaly_z_threshold ?? 3),
          min_samples: Number(values.anomaly_min_samples ?? 10),
        };
      } else if (values.ruleMode === "gap") {
        payload.rule_type = "telemetry_gap";
        payload.gap_conditions = {
          metric_name: values.gap_metric_name ?? "",
          gap_minutes: Number(values.gap_minutes ?? 10),
        };
      } else if (values.ruleMode === "window") {
        payload.rule_type = "window";
        payload.metric_name = values.metric_name ?? "";
        payload.operator = (values.operator ?? "GT") as RuleOperator;
        payload.threshold = Number(values.threshold ?? 0);
        payload.aggregation = values.window_aggregation as AlertRuleCreate["aggregation"];
        payload.window_seconds = Number(values.window_seconds ?? 300);
      } else if (values.ruleMode === "multi") {
        payload.rule_type = "threshold";
        payload.match_mode = values.match_mode ?? "all";
        payload.conditions = (values.conditions ?? []).map((c) => ({
          metric_name: c.metric_name.trim(),
          operator: c.operator,
          threshold: Number(c.threshold),
          duration_minutes: c.duration_minutes == null ? null : Number(c.duration_minutes),
        }));
      } else {
        payload.rule_type = "threshold";
        payload.metric_name = values.metric_name ?? "";
        payload.operator = (values.operator ?? "GT") as RuleOperator;
        payload.threshold = Number(values.threshold ?? 0);
      }
      await createMutation.mutateAsync(payload);
      onClose();
      return;
    }

    if (!rule) return;
    const updates: AlertRuleUpdate = {
      name: values.name,
      severity: values.severity,
      duration_minutes: durationMinutesValue,
      duration_seconds: durationMinutesValue == null ? 0 : durationMinutesValue * 60,
      description: normalizedDescription,
      enabled: values.enabled,
      group_ids: values.group_ids,
      device_group_id: values.device_group_id || null,
    };

    if (values.ruleMode === "anomaly") {
      const anomalyConditions = {
        metric_name: values.anomaly_metric_name ?? "",
        window_minutes: Number(values.anomaly_window_minutes ?? 60),
        z_threshold: Number(values.anomaly_z_threshold ?? 3),
        min_samples: Number(values.anomaly_min_samples ?? 10),
      };
      updates.rule_type = "anomaly";
      updates.anomaly_conditions = anomalyConditions;
      updates.gap_conditions = null;
      updates.conditions = null;
      updates.metric_name = anomalyConditions.metric_name;
      updates.operator = "GT";
      updates.threshold = anomalyConditions.z_threshold;
    } else if (values.ruleMode === "gap") {
      const gapConditions = {
        metric_name: values.gap_metric_name ?? "",
        gap_minutes: Number(values.gap_minutes ?? 10),
      };
      updates.rule_type = "telemetry_gap";
      updates.gap_conditions = gapConditions;
      updates.anomaly_conditions = null;
      updates.conditions = null;
      updates.metric_name = gapConditions.metric_name;
      updates.operator = "GT";
      updates.threshold = gapConditions.gap_minutes;
    } else if (values.ruleMode === "window") {
      updates.rule_type = "window";
      updates.metric_name = values.metric_name ?? "";
      updates.operator = (values.operator ?? "GT") as RuleOperator;
      updates.threshold = Number(values.threshold ?? 0);
      updates.aggregation = values.window_aggregation as AlertRuleUpdate["aggregation"];
      updates.window_seconds = Number(values.window_seconds ?? 300);
      updates.conditions = null;
      updates.anomaly_conditions = null;
      updates.gap_conditions = null;
    } else if (values.ruleMode === "multi") {
      updates.rule_type = "threshold";
      updates.match_mode = values.match_mode ?? "all";
      updates.conditions = (values.conditions ?? []).map((c) => ({
        metric_name: c.metric_name.trim(),
        operator: c.operator,
        threshold: Number(c.threshold),
        duration_minutes: c.duration_minutes == null ? null : Number(c.duration_minutes),
      }));
      updates.anomaly_conditions = null;
      updates.gap_conditions = null;
    } else {
      updates.rule_type = "threshold";
      updates.metric_name = values.metric_name ?? "";
      updates.operator = (values.operator ?? "GT") as RuleOperator;
      updates.threshold = Number(values.threshold ?? 0);
      updates.conditions = null;
      updates.anomaly_conditions = null;
      updates.gap_conditions = null;
    }

    await updateMutation.mutateAsync({ ruleId: String(rule.rule_id), data: updates });
    onClose();
  };

  return (
    <>
      <Dialog
        open={open}
        onOpenChange={(nextOpen) => {
          if (!nextOpen) handleClose();
        }}
      >
        <DialogContent className="max-h-[85vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>{isEditing ? "Edit Alert Rule" : "Create Alert Rule"}</DialogTitle>
          <DialogDescription>
            Define threshold conditions that trigger alerts.
          </DialogDescription>
        </DialogHeader>

        <Form {...form}>
          <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
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
                    {Array.from(new Set(templates.map((tmpl) => tmpl.device_type))).map(
                      (deviceType) => (
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
                      )
                    )}
                  </SelectContent>
                </Select>
              </div>
            )}

            <FormField
              control={form.control}
              name="name"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Rule Name *</FormLabel>
                  <FormControl>
                    <Input placeholder="Battery Low" maxLength={100} {...field} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            <div className="grid gap-2">
              <Label>Rule Mode</Label>
              <div className="flex gap-2">
                <Button
                  type="button"
                  variant={ruleMode === "simple" ? "default" : "outline"}
                  onClick={() => form.setValue("ruleMode", "simple", { shouldDirty: true })}
                >
                  Simple Rule
                </Button>
                <Button
                  type="button"
                  variant={ruleMode === "multi" ? "default" : "outline"}
                  onClick={() => {
                    form.setValue("ruleMode", "multi", { shouldDirty: true });
                    const existing = form.getValues("conditions") ?? [];
                    if (existing.length === 0) {
                      form.setValue(
                        "conditions",
                        [{ metric_name: "", operator: "GT", threshold: 0, duration_minutes: null }],
                        { shouldDirty: true }
                      );
                    }
                    form.setValue("match_mode", "all", { shouldDirty: false });
                  }}
                >
                  Multi-Condition Rule
                </Button>
                <Button
                  type="button"
                  variant={ruleMode === "anomaly" ? "default" : "outline"}
                  onClick={() => form.setValue("ruleMode", "anomaly", { shouldDirty: true })}
                >
                  Anomaly Detection
                </Button>
                <Button
                  type="button"
                  variant={ruleMode === "gap" ? "default" : "outline"}
                  onClick={() => form.setValue("ruleMode", "gap", { shouldDirty: true })}
                >
                  Data Gap
                </Button>
                <Button
                  type="button"
                  variant={ruleMode === "window" ? "default" : "outline"}
                  onClick={() => form.setValue("ruleMode", "window", { shouldDirty: true })}
                >
                  Window Aggregation
                </Button>
              </div>
            </div>

            {ruleMode === "simple" ? (
              <>
                <FormField
                  control={form.control}
                  name="metric_name"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Metric Name *</FormLabel>
                      <div className="flex items-center gap-2">
                        <Select value={(field.value as string) || undefined} onValueChange={field.onChange}>
                          <FormControl>
                            <SelectTrigger className="w-full" disabled={metricsLoading}>
                              <SelectValue
                                placeholder={metricsLoading ? "Loading metrics..." : "Select metric"}
                              />
                            </SelectTrigger>
                          </FormControl>
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
                      <FormDescription className="text-xs">
                        {metricsLoading
                          ? "Loading metric reference..."
                          : normalizedMetrics.length === 0 && rawMetrics.length === 0
                            ? "No metrics found. Metrics will appear after devices send telemetry."
                            : selectedNormalized
                              ? `Includes: ${selectedNormalized.mapped_from.join(", ") || "none"}`
                              : "Select a metric to see details."}
                      </FormDescription>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                <FormField
                  control={form.control}
                  name="operator"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Operator</FormLabel>
                      <Select value={(field.value as string) || "GT"} onValueChange={field.onChange}>
                        <FormControl>
                          <SelectTrigger className="w-full">
                            <SelectValue placeholder="Select operator" />
                          </SelectTrigger>
                        </FormControl>
                        <SelectContent>
                          <SelectItem value="GT">&gt; (GT)</SelectItem>
                          <SelectItem value="LT">&lt; (LT)</SelectItem>
                          <SelectItem value="GTE">≥ (GTE)</SelectItem>
                          <SelectItem value="LTE">≤ (LTE)</SelectItem>
                          <SelectItem value="EQ">= (EQ)</SelectItem>
                          <SelectItem value="NEQ">!= (NEQ)</SelectItem>
                        </SelectContent>
                      </Select>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                <FormField
                  control={form.control}
                  name="threshold"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Threshold *</FormLabel>
                      <FormControl>
                        <Input
                          type="number"
                          step="any"
                          value={(field.value as unknown as string) ?? ""}
                          onChange={field.onChange}
                        />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
              </>
            ) : ruleMode === "multi" ? (
              <div className="space-y-3 rounded-md border border-border p-3">
                {multiConditions.length > 1 && (
                  <div className="flex items-center gap-3">
                    <Label>Match</Label>
                    <label className="inline-flex items-center gap-2 text-sm">
                      <input
                        type="radio"
                        value="all"
                        checked={matchMode === "all"}
                        onChange={() => form.setValue("match_mode", "all", { shouldDirty: true })}
                      />
                      ALL (AND)
                    </label>
                    <label className="inline-flex items-center gap-2 text-sm">
                      <input
                        type="radio"
                        value="any"
                        checked={matchMode === "any"}
                        onChange={() => form.setValue("match_mode", "any", { shouldDirty: true })}
                      />
                      ANY (OR)
                    </label>
                  </div>
                )}

                {typeof (form.formState.errors as any)?.conditions?.message === "string" && (
                  <div className="text-sm font-medium text-destructive">
                    {(form.formState.errors as any).conditions.message}
                  </div>
                )}

                <div className="grid gap-2 text-xs text-muted-foreground md:grid-cols-[1fr_210px_120px_160px_auto]">
                  <span>Metric</span>
                  <span>Operator</span>
                  <span>Threshold</span>
                  <span>Duration (min)</span>
                  <span />
                </div>
                {multiConditions.map((condition, index) => (
                  <div key={`${index}-${condition.metric_name}`} className="space-y-1">
                    <ConditionRow
                      condition={condition}
                      index={index}
                      onChange={updateCondition}
                      onRemove={removeCondition}
                      canRemove={multiConditions.length > 1}
                    />
                    {(form.formState.errors as any)?.conditions?.[index] && (
                      <div className="text-sm text-destructive">
                        {(form.formState.errors as any).conditions[index]?.metric_name?.message ||
                          (form.formState.errors as any).conditions[index]?.threshold?.message ||
                          ""}
                      </div>
                    )}
                  </div>
                ))}
                <Button
                  type="button"
                  variant="outline"
                  disabled={multiConditions.length >= 10}
                  onClick={addCondition}
                >
                  Add Condition
                </Button>
              </div>
            ) : ruleMode === "anomaly" ? (
              <div className="space-y-3 rounded-md border border-border p-3">
                <FormField
                  control={form.control}
                  name="anomaly_metric_name"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Metric Name *</FormLabel>
                      <FormControl>
                        <Input placeholder="temperature" {...field} />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                <FormField
                  control={form.control}
                  name="anomaly_window_minutes"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Window</FormLabel>
                      <Select
                        value={String(field.value ?? 60)}
                        onValueChange={(v) => field.onChange(Number(v))}
                      >
                        <FormControl>
                          <SelectTrigger className="w-full">
                            <SelectValue />
                          </SelectTrigger>
                        </FormControl>
                        <SelectContent>
                          <SelectItem value="15">15 min</SelectItem>
                          <SelectItem value="30">30 min</SelectItem>
                          <SelectItem value="60">1 hour</SelectItem>
                          <SelectItem value="360">6 hours</SelectItem>
                          <SelectItem value="1440">24 hours</SelectItem>
                        </SelectContent>
                      </Select>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                <FormField
                  control={form.control}
                  name="anomaly_z_threshold"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Z-Score Threshold</FormLabel>
                      <FormControl>
                        <Input
                          type="number"
                          min={1}
                          max={10}
                          step="0.1"
                          value={String(field.value ?? 3)}
                          onChange={(e) => field.onChange(e.target.value)}
                        />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                <FormField
                  control={form.control}
                  name="anomaly_min_samples"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Min Samples</FormLabel>
                      <FormControl>
                        <Input
                          type="number"
                          min={3}
                          step={1}
                          value={String(field.value ?? 10)}
                          onChange={(e) => field.onChange(e.target.value)}
                        />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
              </div>
            ) : ruleMode === "gap" ? (
              <div className="space-y-3 rounded-md border border-border p-3">
                <FormField
                  control={form.control}
                  name="gap_metric_name"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Metric Name *</FormLabel>
                      <FormControl>
                        <Input placeholder="temperature" {...field} />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                <FormField
                  control={form.control}
                  name="gap_minutes"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Gap Threshold (minutes)</FormLabel>
                      <FormControl>
                        <Input
                          type="number"
                          min={1}
                          step={1}
                          value={String(field.value ?? 10)}
                          onChange={(e) => field.onChange(e.target.value)}
                        />
                      </FormControl>
                      <FormDescription className="text-xs">
                        Alert if no {gapMetricName || "metric"} data for {gapMinutes || "0"} minutes.
                      </FormDescription>
                      <FormMessage />
                    </FormItem>
                  )}
                />
              </div>
            ) : ruleMode === "window" ? (
              <div className="space-y-3 rounded-md border border-border p-3">
                <FormField
                  control={form.control}
                  name="metric_name"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Metric Name *</FormLabel>
                      <Select value={(field.value as string) || undefined} onValueChange={field.onChange}>
                        <FormControl>
                          <SelectTrigger className="w-full" disabled={metricsLoading}>
                            <SelectValue
                              placeholder={metricsLoading ? "Loading metrics..." : "Select metric"}
                            />
                          </SelectTrigger>
                        </FormControl>
                        <SelectContent>
                          <SelectGroup>
                            <SelectLabel>Normalized</SelectLabel>
                            {normalizedMetrics.map((metric) => (
                              <SelectItem key={metric.name} value={metric.name}>
                                {metric.name}
                                {metric.display_unit ? ` (${metric.display_unit})` : ""}
                              </SelectItem>
                            ))}
                          </SelectGroup>
                          <SelectGroup>
                            <SelectLabel>Raw</SelectLabel>
                            {rawMetrics.map((metric) => (
                              <SelectItem key={metric.name} value={metric.name}>
                                {metric.name}
                              </SelectItem>
                            ))}
                          </SelectGroup>
                        </SelectContent>
                      </Select>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                <FormField
                  control={form.control}
                  name="window_aggregation"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Aggregation</FormLabel>
                      <Select value={String(field.value ?? "avg")} onValueChange={field.onChange}>
                        <FormControl>
                          <SelectTrigger className="w-full">
                            <SelectValue />
                          </SelectTrigger>
                        </FormControl>
                        <SelectContent>
                          <SelectItem value="avg">Average (avg)</SelectItem>
                          <SelectItem value="min">Minimum (min)</SelectItem>
                          <SelectItem value="max">Maximum (max)</SelectItem>
                          <SelectItem value="count">Count</SelectItem>
                          <SelectItem value="sum">Sum</SelectItem>
                        </SelectContent>
                      </Select>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                <FormField
                  control={form.control}
                  name="operator"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Operator</FormLabel>
                      <Select value={(field.value as string) || "GT"} onValueChange={field.onChange}>
                        <FormControl>
                          <SelectTrigger className="w-full">
                            <SelectValue />
                          </SelectTrigger>
                        </FormControl>
                        <SelectContent>
                          <SelectItem value="GT">&gt; (GT)</SelectItem>
                          <SelectItem value="LT">&lt; (LT)</SelectItem>
                          <SelectItem value="GTE">≥ (GTE)</SelectItem>
                          <SelectItem value="LTE">≤ (LTE)</SelectItem>
                          <SelectItem value="EQ">= (EQ)</SelectItem>
                          <SelectItem value="NEQ">!= (NEQ)</SelectItem>
                        </SelectContent>
                      </Select>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                <FormField
                  control={form.control}
                  name="threshold"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Threshold *</FormLabel>
                      <FormControl>
                        <Input
                          type="number"
                          step="any"
                          value={(field.value as unknown as string) ?? ""}
                          onChange={field.onChange}
                        />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                <FormField
                  control={form.control}
                  name="window_seconds"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Window Duration</FormLabel>
                      <Select
                        value={String(field.value ?? 300)}
                        onValueChange={(v) => field.onChange(Number(v))}
                      >
                        <FormControl>
                          <SelectTrigger className="w-full">
                            <SelectValue />
                          </SelectTrigger>
                        </FormControl>
                        <SelectContent>
                          <SelectItem value="60">1 minute</SelectItem>
                          <SelectItem value="120">2 minutes</SelectItem>
                          <SelectItem value="300">5 minutes</SelectItem>
                          <SelectItem value="600">10 minutes</SelectItem>
                          <SelectItem value="900">15 minutes</SelectItem>
                          <SelectItem value="1800">30 minutes</SelectItem>
                          <SelectItem value="3600">1 hour</SelectItem>
                        </SelectContent>
                      </Select>
                      <FormDescription className="text-xs">
                        Alert fires when {windowAggregation}({metricName || "metric"}) breaches the
                        threshold over a {Number(windowSeconds) / 60}-minute sliding window.
                      </FormDescription>
                      <FormMessage />
                    </FormItem>
                  )}
                />
              </div>
            ) : null}

            <FormField
              control={form.control}
              name="device_group_id"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Scope to Device Group</FormLabel>
                  <Select
                    value={(field.value as string) || "none"}
                    onValueChange={(v) => field.onChange(v === "none" ? "" : v)}
                  >
                    <FormControl>
                      <SelectTrigger className="w-full">
                        <SelectValue placeholder="All devices (no group filter)" />
                      </SelectTrigger>
                    </FormControl>
                    <SelectContent>
                      <SelectItem value="none">All devices (no group filter)</SelectItem>
                      {(deviceGroupsResponse?.groups ?? []).map((group: DeviceGroup) => (
                        <SelectItem key={group.group_id} value={group.group_id}>
                          {group.name} ({group.member_count ?? 0} devices)
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  <FormDescription className="text-xs">
                    If set, this rule only evaluates devices in the selected group.
                  </FormDescription>
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="group_ids"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Device Groups</FormLabel>
                  <div className="max-h-40 space-y-2 overflow-auto rounded-md border border-border p-2">
                    {(deviceGroupsResponse?.groups ?? []).length === 0 ? (
                      <p className="text-xs text-muted-foreground">No device groups yet.</p>
                    ) : (
                      (deviceGroupsResponse?.groups ?? []).map((group: DeviceGroup) => {
                        const checked = (field.value as string[])?.includes(group.group_id);
                        return (
                          <label
                            key={group.group_id}
                            className="flex items-center justify-between gap-2 text-sm"
                          >
                            <span>{group.name}</span>
                            <input
                              type="checkbox"
                              checked={Boolean(checked)}
                              onChange={(e) => {
                                const current = Array.isArray(field.value) ? [...field.value] : [];
                                if (e.target.checked) {
                                  field.onChange([...new Set([...current, group.group_id])]);
                                } else {
                                  field.onChange(current.filter((id) => id !== group.group_id));
                                }
                              }}
                            />
                          </label>
                        );
                      })
                    )}
                  </div>
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="duration_minutes"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Duration (minutes)</FormLabel>
                  <FormControl>
                    <Input
                      type="number"
                      min={1}
                      step={1}
                      placeholder="Instant (leave blank)"
                      value={field.value == null ? "" : String(field.value)}
                      onChange={field.onChange}
                    />
                  </FormControl>
                  <FormDescription className="text-xs">
                    Fire only after condition holds for this many minutes. Leave blank to fire
                    immediately.
                  </FormDescription>
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="severity"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Severity</FormLabel>
                  <Select value={String(field.value ?? 3)} onValueChange={(v) => field.onChange(Number(v))}>
                    <FormControl>
                      <SelectTrigger className="w-full">
                        <SelectValue placeholder="Select severity" />
                      </SelectTrigger>
                    </FormControl>
                    <SelectContent>
                      <SelectItem value="1">1 (Info)</SelectItem>
                      <SelectItem value="2">2 (Low)</SelectItem>
                      <SelectItem value="3">3 (Medium)</SelectItem>
                      <SelectItem value="4">4 (High)</SelectItem>
                      <SelectItem value="5">5 (Critical)</SelectItem>
                    </SelectContent>
                  </Select>
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="description"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Description</FormLabel>
                  <FormControl>
                    <Textarea placeholder="Optional context for this rule" {...field} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="enabled"
              render={({ field }) => (
                <div className="flex items-center justify-between rounded-md border border-border p-3">
                  <div>
                    <Label className="text-sm">Enabled</Label>
                    <p className="text-xs text-muted-foreground">Alerts will trigger when enabled.</p>
                  </div>
                  <Switch checked={Boolean(field.value)} onCheckedChange={field.onChange} />
                </div>
              )}
            />

            {errorMessage && <div className="text-sm text-destructive">{errorMessage}</div>}

            <DialogFooter>
              <Button type="button" variant="outline" onClick={handleClose}>
                Cancel
              </Button>
              <Button type="submit" disabled={isSaving}>
                {isSaving ? "Saving..." : isEditing ? "Save Changes" : "Create Rule"}
              </Button>
            </DialogFooter>
          </form>
        </Form>
        </DialogContent>
      </Dialog>

      <AlertDialog open={showConfirm} onOpenChange={cancelDiscard}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Discard changes?</AlertDialogTitle>
            <AlertDialogDescriptionText>
              You have unsaved changes. Are you sure you want to close without saving?
            </AlertDialogDescriptionText>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel onClick={cancelDiscard}>Keep Editing</AlertDialogCancel>
            <AlertDialogAction
              onClick={confirmDiscard}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              Discard
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  );
}
