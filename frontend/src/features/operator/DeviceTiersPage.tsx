import { useEffect, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { Plus, Pencil } from "lucide-react";
import { PageHeader } from "@/components/shared";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Switch } from "@/components/ui/switch";
import { Textarea } from "@/components/ui/textarea";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import {
  createDevicePlan,
  deactivateDevicePlan,
  fetchDevicePlans,
  updateDevicePlan,
  type OperatorDevicePlan,
} from "@/services/api/device-tiers";
import { z } from "zod";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { Form, FormControl, FormField, FormItem, FormLabel, FormMessage } from "@/components/ui/form";

const KNOWN_FEATURES = [
  "ota_updates",
  "advanced_analytics",
  "streaming_export",
  "x509_auth",
  "message_routing",
  "device_commands",
  "device_twin",
  "carrier_diagnostics",
] as const;

const KNOWN_LIMITS = [
  { key: "sensors", label: "Sensors" },
  { key: "data_retention_days", label: "Data Retention (days)" },
  { key: "telemetry_rate_per_minute", label: "Telemetry Rate (msg/min)" },
  { key: "health_telemetry_interval_seconds", label: "Health Interval (sec)" },
] as const;

function FeatureBadges({ features }: { features: Record<string, boolean> }) {
  return (
    <div className="flex flex-wrap gap-1">
      {KNOWN_FEATURES.map((f) => {
        const enabled = !!features?.[f];
        return (
          <Badge
            key={f}
            variant="outline"
            className={enabled ? "bg-green-100 text-green-800" : "text-muted-foreground"}
          >
            {f}
          </Badge>
        );
      })}
    </div>
  );
}

function makeDefaultFeatures(): Record<string, boolean> {
  const out: Record<string, boolean> = {};
  for (const f of KNOWN_FEATURES) out[f] = false;
  return out;
}

function makeDefaultLimits(): Record<string, number> {
  const out: Record<string, number> = {};
  for (const l of KNOWN_LIMITS) out[l.key] = 0;
  return out;
}

type DialogMode = { mode: "create" } | { mode: "edit"; plan: OperatorDevicePlan };

const devicePlanSchema = z.object({
  plan_id: z
    .string()
    .min(2)
    .max(50)
    .regex(/^[a-z0-9_-]+$/, "Lowercase alphanumeric with hyphens/underscores"),
  name: z.string().min(2).max(100),
  description: z.string().max(500).optional().or(z.literal("")),
  limits: z.record(z.string(), z.coerce.number()).optional(),
  features: z.record(z.string(), z.boolean()).optional(),
  monthly_price_cents: z.coerce.number().int().min(0),
  annual_price_cents: z.coerce.number().int().min(0),
  sort_order: z.coerce.number().int().min(0).optional(),
  is_active: z.boolean().optional(),
});

type DevicePlanFormValues = z.infer<typeof devicePlanSchema>;

function mapPlanToFormValues(plan: OperatorDevicePlan): DevicePlanFormValues {
  return {
    plan_id: plan.plan_id,
    name: plan.name,
    description: plan.description || "",
    limits: { ...makeDefaultLimits(), ...(plan.limits || {}) },
    features: { ...makeDefaultFeatures(), ...(plan.features || {}) },
    monthly_price_cents: plan.monthly_price_cents ?? 0,
    annual_price_cents: plan.annual_price_cents ?? 0,
    sort_order: plan.sort_order ?? 0,
    is_active: Boolean(plan.is_active),
  };
}

export default function DeviceTiersPage() {
  const queryClient = useQueryClient();

  const { data, isLoading } = useQuery({
    queryKey: ["operator-device-plans"],
    queryFn: fetchDevicePlans,
  });

  const plans = data?.plans ?? [];
  const sorted = useMemo(
    () => [...plans].sort((a, b) => (a.sort_order ?? 0) - (b.sort_order ?? 0)),
    [plans]
  );

  const [dialog, setDialog] = useState<DialogMode | null>(null);

  const defaultCreateValues: DevicePlanFormValues = useMemo(
    () => ({
      plan_id: "",
      name: "",
      description: "",
      limits: makeDefaultLimits(),
      features: makeDefaultFeatures(),
      monthly_price_cents: 0,
      annual_price_cents: 0,
      sort_order: 0,
      is_active: true,
    }),
    []
  );

  const form = useForm<DevicePlanFormValues>({
    resolver: zodResolver(devicePlanSchema) as any,
    defaultValues: defaultCreateValues,
  });

  useEffect(() => {
    if (!dialog) return;
    if (dialog.mode === "create") {
      form.reset(defaultCreateValues);
      return;
    }
    form.reset(mapPlanToFormValues(dialog.plan));
  }, [defaultCreateValues, dialog, form]);

  const createMutation = useMutation({
    mutationFn: async (values: DevicePlanFormValues) => {
      const order = values.sort_order ?? 0;
      return createDevicePlan({
        plan_id: values.plan_id.trim(),
        name: values.name.trim(),
        description: values.description?.trim() || undefined,
        limits: values.limits || makeDefaultLimits(),
        features: values.features || makeDefaultFeatures(),
        monthly_price_cents: values.monthly_price_cents,
        annual_price_cents: values.annual_price_cents,
        sort_order: Number.isFinite(order) ? order : 0,
      });
    },
    onSuccess: () => {
      toast.success("Device plan created");
      void queryClient.invalidateQueries({ queryKey: ["operator-device-plans"] });
      setDialog(null);
    },
    onError: (err: any) => toast.error(err?.message || "Failed to create plan"),
  });

  const updateMutation = useMutation({
    mutationFn: async (args: { planId: string; values: DevicePlanFormValues }) => {
      const order = args.values.sort_order ?? 0;
      return updateDevicePlan(args.planId, {
        name: args.values.name.trim() || undefined,
        description: args.values.description?.trim() || undefined,
        limits: args.values.limits,
        features: args.values.features,
        monthly_price_cents: args.values.monthly_price_cents,
        annual_price_cents: args.values.annual_price_cents,
        sort_order: Number.isFinite(order) ? order : 0,
        is_active: Boolean(args.values.is_active),
      });
    },
    onSuccess: () => {
      toast.success("Device plan updated");
      void queryClient.invalidateQueries({ queryKey: ["operator-device-plans"] });
      setDialog(null);
    },
    onError: (err: any) => toast.error(err?.message || "Failed to update plan"),
  });

  const activeToggleMutation = useMutation({
    mutationFn: async (args: { planId: string; next: boolean }) => {
      if (!args.next) {
        await deactivateDevicePlan(args.planId);
        return;
      }
      return updateDevicePlan(args.planId, { is_active: true });
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["operator-device-plans"] });
    },
    onError: (err: any) => toast.error(err?.message || "Failed to update active status"),
  });

  function setFeature(name: string, value: boolean) {
    form.setValue(`features.${name}` as any, value, { shouldDirty: true });
  }

  function setLimit(name: string, value: number) {
    form.setValue(`limits.${name}` as any, value, { shouldDirty: true });
  }

  function onSubmit(values: DevicePlanFormValues) {
    if (!dialog) return;
    if (dialog.mode === "create") {
      createMutation.mutate(values);
    } else {
      updateMutation.mutate({ planId: dialog.plan.plan_id, values });
    }
  }

  return (
    <div className="space-y-4">
      <PageHeader
        title="Device Plans"
        description="Manage per-device plan definitions (limits, features, pricing)."
      />

      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle>Plans</CardTitle>
          <Button size="sm" onClick={() => setDialog({ mode: "create" })}>
            <Plus className="mr-2 h-4 w-4" />
            Create Plan
          </Button>
        </CardHeader>
        <CardContent>
          <div className="rounded-md border">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Plan ID</TableHead>
                  <TableHead>Name</TableHead>
                  <TableHead>Limits</TableHead>
                  <TableHead>Features</TableHead>
                  <TableHead>Price</TableHead>
                  <TableHead>Sort</TableHead>
                  <TableHead>Active</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {!isLoading && sorted.length === 0 && (
                  <TableRow>
                    <TableCell colSpan={8} className="text-sm text-muted-foreground">
                      No device plans found.
                    </TableCell>
                  </TableRow>
                )}
                {sorted.map((p) => (
                  <TableRow key={p.plan_id}>
                    <TableCell className="font-mono text-sm">{p.plan_id}</TableCell>
                    <TableCell>{p.name}</TableCell>
                    <TableCell className="text-xs text-muted-foreground">
                      {KNOWN_LIMITS.map((l) => (
                        <div key={l.key}>
                          {l.key}: {p.limits?.[l.key] ?? "—"}
                        </div>
                      ))}
                    </TableCell>
                    <TableCell>
                      <FeatureBadges features={p.features || {}} />
                    </TableCell>
                    <TableCell className="text-sm">
                      ${(p.monthly_price_cents / 100).toFixed(2)}/mo
                    </TableCell>
                    <TableCell>{p.sort_order}</TableCell>
                    <TableCell>
                      <Switch
                        checked={!!p.is_active}
                        onCheckedChange={(next) =>
                          activeToggleMutation.mutate({ planId: p.plan_id, next })
                        }
                      />
                    </TableCell>
                    <TableCell className="text-right">
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => setDialog({ mode: "edit", plan: p })}
                      >
                        <Pencil className="mr-2 h-4 w-4" />
                        Edit
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        </CardContent>
      </Card>

      <Dialog open={!!dialog} onOpenChange={(open) => (!open ? setDialog(null) : null)}>
        <DialogContent className="max-h-[80vh] max-w-2xl overflow-y-auto">
          <DialogHeader>
            <DialogTitle>
              {dialog?.mode === "create"
                ? "Create Device Plan"
                : `Edit Device Plan: ${dialog?.mode === "edit" ? dialog.plan.plan_id : ""}`}
            </DialogTitle>
          </DialogHeader>

          <Form {...form}>
            <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
              {dialog?.mode === "create" && (
                <FormField
                  control={form.control}
                  name="plan_id"
                  render={({ field }) => (
                    <FormItem className="space-y-2">
                      <FormLabel>Plan ID</FormLabel>
                      <FormControl>
                        <Input id="plan-id" placeholder="basic" {...field} />
                      </FormControl>
                      <p className="text-sm text-muted-foreground">
                        Lowercase identifier (used in APIs and seed data).
                      </p>
                      <FormMessage />
                    </FormItem>
                  )}
                />
              )}

              <FormField
                control={form.control}
                name="name"
                render={({ field }) => (
                  <FormItem className="space-y-2">
                    <FormLabel>Name</FormLabel>
                    <FormControl>
                      <Input id="plan-name" placeholder="Basic" {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <FormField
                control={form.control}
                name="description"
                render={({ field }) => (
                  <FormItem className="space-y-2">
                    <FormLabel>Description</FormLabel>
                    <FormControl>
                      <Textarea
                        id="plan-description"
                        placeholder="Describe what this plan enables..."
                        {...field}
                      />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <fieldset className="space-y-3 rounded-md border p-4">
                <legend className="px-1 text-sm font-medium">Limits</legend>
                <div className="grid gap-3 md:grid-cols-2">
                  {KNOWN_LIMITS.map((l) => (
                    <div key={l.key} className="space-y-2">
                      <div className="text-sm font-medium">{l.label}</div>
                      <Input
                        type="number"
                        value={Number(form.watch(`limits.${l.key}` as any) ?? 0)}
                        onChange={(e) => setLimit(l.key, Number(e.target.value))}
                      />
                    </div>
                  ))}
                </div>
              </fieldset>

              <fieldset className="space-y-3 rounded-md border p-4">
                <legend className="px-1 text-sm font-medium">Features</legend>
                <div className="grid gap-3 md:grid-cols-2">
                  {KNOWN_FEATURES.map((f) => (
                    <div key={f} className="flex items-center justify-between gap-3">
                      <span className="font-mono text-sm">{f}</span>
                      <Switch
                        checked={Boolean(form.watch(`features.${f}` as any))}
                        onCheckedChange={(v) => setFeature(f, v)}
                      />
                    </div>
                  ))}
                </div>
              </fieldset>

              <div className="grid gap-3 md:grid-cols-2">
                <FormField
                  control={form.control}
                  name="monthly_price_cents"
                  render={({ field }) => (
                    <FormItem className="space-y-2">
                      <FormLabel>Monthly Price (cents)</FormLabel>
                      <FormControl>
                        <Input
                          id="plan-monthly-price"
                          type="number"
                          value={field.value ?? 0}
                          onChange={(e) => field.onChange(e.target.value)}
                        />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                <FormField
                  control={form.control}
                  name="annual_price_cents"
                  render={({ field }) => (
                    <FormItem className="space-y-2">
                      <FormLabel>Annual Price (cents)</FormLabel>
                      <FormControl>
                        <Input
                          id="plan-annual-price"
                          type="number"
                          value={field.value ?? 0}
                          onChange={(e) => field.onChange(e.target.value)}
                        />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
              </div>

              <div className="grid gap-3 md:grid-cols-2">
                <FormField
                  control={form.control}
                  name="sort_order"
                  render={({ field }) => (
                    <FormItem className="space-y-2">
                      <FormLabel>Sort Order</FormLabel>
                      <FormControl>
                        <Input
                          id="plan-sort-order"
                          type="number"
                          value={field.value ?? 0}
                          onChange={(e) => field.onChange(e.target.value)}
                        />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                {dialog?.mode === "edit" && (
                  <FormField
                    control={form.control}
                    name="is_active"
                    render={({ field }) => (
                      <FormItem className="flex items-center justify-between rounded-md border p-3">
                        <div className="space-y-0.5">
                          <div className="text-sm font-medium">Active</div>
                          <div className="text-sm text-muted-foreground">
                            Disable to hide plan from customers.
                          </div>
                        </div>
                        <FormControl>
                          <Switch checked={Boolean(field.value)} onCheckedChange={field.onChange} />
                        </FormControl>
                      </FormItem>
                    )}
                  />
                )}
              </div>

              <div className="flex justify-end gap-2 pt-2">
                <Button type="button" variant="outline" onClick={() => setDialog(null)}>
                  Cancel
                </Button>
                <Button type="submit" disabled={createMutation.isPending || updateMutation.isPending}>
                  {dialog?.mode === "create"
                    ? createMutation.isPending
                      ? "Creating..."
                      : "Create"
                    : updateMutation.isPending
                      ? "Saving..."
                      : "Save"}
                </Button>
              </div>
            </form>
          </Form>
        </DialogContent>
      </Dialog>
    </div>
  );
}

