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
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  createDeviceTier,
  fetchDeviceTiers,
  updateDeviceTier,
  type OperatorDeviceTier,
} from "@/services/api/device-tiers";
import { z } from "zod";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";

const KNOWN_FEATURES = [
  "telemetry",
  "alerts",
  "dashboards",
  "ota",
  "analytics",
  "x509_auth",
  "streaming_export",
  "message_routing",
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

type DialogMode = { mode: "create" } | { mode: "edit"; tier: OperatorDeviceTier };

const deviceTierSchema = z.object({
  name: z.string().min(2, "Tier name required").max(50),
  display_name: z.string().min(2, "Display name required").max(100),
  description: z.string().max(500).optional().or(z.literal("")),
  // Zod v4: record requires key schema + value schema.
  features: z.record(z.string(), z.boolean()).optional(),
  sort_order: z.coerce.number().int().min(0, "Must be non-negative").optional(),
  is_active: z.boolean().optional(),
});

type DeviceTierFormValues = z.infer<typeof deviceTierSchema>;

function mapTierToFormValues(tier: OperatorDeviceTier): DeviceTierFormValues {
  return {
    name: tier.name,
    display_name: tier.display_name || "",
    description: tier.description || "",
    features: { ...makeDefaultFeatures(), ...(tier.features || {}) },
    sort_order: tier.sort_order ?? 0,
    is_active: Boolean(tier.is_active),
  };
}

export default function DeviceTiersPage() {
  const queryClient = useQueryClient();
  const { data, isLoading } = useQuery({
    queryKey: ["operator-device-tiers"],
    queryFn: fetchDeviceTiers,
  });

  const tiers = data?.tiers ?? [];
  const sorted = useMemo(
    () => [...tiers].sort((a, b) => a.sort_order - b.sort_order),
    [tiers]
  );

  const [dialog, setDialog] = useState<DialogMode | null>(null);

  const defaultCreateValues: DeviceTierFormValues = useMemo(
    () => ({
      name: "",
      display_name: "",
      description: "",
      features: makeDefaultFeatures(),
      sort_order: 0,
      is_active: true,
    }),
    []
  );

  const form = useForm<DeviceTierFormValues>({
    // zodResolver types can get confused with Zod v4 coercion; runtime validation is correct.
    resolver: zodResolver(deviceTierSchema) as any,
    defaultValues: defaultCreateValues,
  });

  useEffect(() => {
    if (!dialog) return;
    if (dialog.mode === "create") {
      form.reset(defaultCreateValues);
      return;
    }
    form.reset(mapTierToFormValues(dialog.tier));
  }, [defaultCreateValues, dialog, form]);

  const createMutation = useMutation({
    mutationFn: async (values: DeviceTierFormValues) => {
      const order = values.sort_order ?? 0;
      const payload = {
        name: values.name.trim().toLowerCase(),
        display_name: values.display_name.trim(),
        description: values.description?.trim() || undefined,
        features: values.features || makeDefaultFeatures(),
        sort_order: Number.isFinite(order) ? order : 0,
      };
      return createDeviceTier(payload);
    },
    onSuccess: () => {
      toast.success("Device tier created");
      void queryClient.invalidateQueries({ queryKey: ["operator-device-tiers"] });
      setDialog(null);
    },
    onError: (err: any) => toast.error(err?.message || "Failed to create tier"),
  });

  const updateMutation = useMutation({
    mutationFn: async (args: { tierId: number; values: DeviceTierFormValues }) => {
      const order = args.values.sort_order ?? 0;
      return updateDeviceTier(args.tierId, {
        display_name: args.values.display_name.trim() || undefined,
        description: args.values.description?.trim() || undefined,
        features: args.values.features || makeDefaultFeatures(),
        sort_order: Number.isFinite(order) ? order : 0,
        is_active: Boolean(args.values.is_active),
      });
    },
    onSuccess: () => {
      toast.success("Device tier updated");
      void queryClient.invalidateQueries({ queryKey: ["operator-device-tiers"] });
      setDialog(null);
    },
    onError: (err: any) => toast.error(err?.message || "Failed to update tier"),
  });

  const activeToggleMutation = useMutation({
    mutationFn: async (args: { tierId: number; next: boolean }) => {
      return updateDeviceTier(args.tierId, { is_active: args.next });
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["operator-device-tiers"] });
    },
    onError: (err: any) => toast.error(err?.message || "Failed to update active status"),
  });

  function setFeature(name: string, value: boolean) {
    form.setValue(`features.${name}` as any, value, { shouldDirty: true });
  }

  function onSubmit(values: DeviceTierFormValues) {
    if (!dialog) return;
    if (dialog.mode === "create") {
      createMutation.mutate(values);
    } else {
      updateMutation.mutate({ tierId: dialog.tier.tier_id, values });
    }
  }

  return (
    <div className="space-y-4">
      <PageHeader
        title="Device Tiers"
        description="Manage tier definitions and feature access for tenant devices."
      />

      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle>Tiers</CardTitle>
          <Button size="sm" onClick={() => setDialog({ mode: "create" })}>
            <Plus className="mr-2 h-4 w-4" />
            Create Tier
          </Button>
        </CardHeader>
        <CardContent>
          <div className="rounded-md border">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Name</TableHead>
                  <TableHead>Display Name</TableHead>
                  <TableHead>Description</TableHead>
                  <TableHead>Features</TableHead>
                  <TableHead>Sort</TableHead>
                  <TableHead>Active</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {!isLoading && sorted.length === 0 && (
                  <TableRow>
                    <TableCell colSpan={7} className="text-sm text-muted-foreground">
                      No device tiers found.
                    </TableCell>
                  </TableRow>
                )}
                {sorted.map((t) => (
                  <TableRow key={t.tier_id}>
                    <TableCell className="font-mono text-sm">{t.name}</TableCell>
                    <TableCell>{t.display_name}</TableCell>
                    <TableCell className="max-w-[260px] truncate">
                      {t.description || "—"}
                    </TableCell>
                    <TableCell>
                      <FeatureBadges features={t.features || {}} />
                    </TableCell>
                    <TableCell>{t.sort_order}</TableCell>
                    <TableCell>
                      <Switch
                        checked={!!t.is_active}
                        onCheckedChange={(next) =>
                          activeToggleMutation.mutate({ tierId: t.tier_id, next })
                        }
                      />
                    </TableCell>
                    <TableCell className="text-right">
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => setDialog({ mode: "edit", tier: t })}
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
        <DialogContent className="max-w-2xl max-h-[80vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>
              {dialog?.mode === "create"
                ? "Create Device Tier"
                : `Edit Device Tier: ${dialog?.mode === "edit" ? dialog.tier.name : ""}`}
            </DialogTitle>
          </DialogHeader>

          <Form {...form}>
            <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
              {dialog?.mode === "create" && (
                <FormField
                  control={form.control}
                  name="name"
                  render={({ field }) => (
                    <FormItem className="space-y-2">
                      <FormLabel>Name</FormLabel>
                      <FormControl>
                        <Input id="tier-name" placeholder="basic" {...field} />
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
                name="display_name"
                render={({ field }) => (
                  <FormItem className="space-y-2">
                    <FormLabel>Display Name</FormLabel>
                    <FormControl>
                      <Input id="tier-display-name" placeholder="Basic" {...field} />
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
                      <Textarea id="tier-description" placeholder="Describe what this tier enables..." {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />

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
                  name="sort_order"
                  render={({ field }) => (
                    <FormItem className="space-y-2">
                      <FormLabel>Sort Order</FormLabel>
                      <FormControl>
                        <Input
                          id="tier-sort-order"
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
                            Disable to hide tier from customers.
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

