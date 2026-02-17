import { useEffect, useMemo, useState, type FormEvent } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { Plus, Pencil } from "lucide-react";
import { PageHeader } from "@/components/shared";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
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

  const [name, setName] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [description, setDescription] = useState("");
  const [features, setFeatures] = useState<Record<string, boolean>>(makeDefaultFeatures());
  const [sortOrder, setSortOrder] = useState("0");
  const [isActive, setIsActive] = useState(true);

  useEffect(() => {
    if (!dialog) return;
    if (dialog.mode === "create") {
      setName("");
      setDisplayName("");
      setDescription("");
      setFeatures(makeDefaultFeatures());
      setSortOrder("0");
      setIsActive(true);
      return;
    }
    const t = dialog.tier;
    setName(t.name);
    setDisplayName(t.display_name);
    setDescription(t.description || "");
    setFeatures({ ...makeDefaultFeatures(), ...(t.features || {}) });
    setSortOrder(String(t.sort_order ?? 0));
    setIsActive(!!t.is_active);
  }, [dialog]);

  const createMutation = useMutation({
    mutationFn: async () => {
      const order = Number.parseInt(sortOrder || "0", 10);
      const payload = {
        name: name.trim().toLowerCase(),
        display_name: displayName.trim(),
        description: description.trim() || undefined,
        features,
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
    mutationFn: async (tierId: number) => {
      const order = Number.parseInt(sortOrder || "0", 10);
      return updateDeviceTier(tierId, {
        display_name: displayName.trim() || undefined,
        description: description.trim() || undefined,
        features,
        sort_order: Number.isFinite(order) ? order : 0,
        is_active: isActive,
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
    setFeatures((prev) => ({ ...prev, [name]: value }));
  }

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (!dialog) return;
    if (dialog.mode === "create") {
      createMutation.mutate();
    } else {
      updateMutation.mutate(dialog.tier.tier_id);
    }
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="Device Tiers"
        description="Manage tier definitions and feature access for tenant devices."
      />

      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle className="text-base">Tiers</CardTitle>
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
                    <TableCell className="font-mono text-xs">{t.name}</TableCell>
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

          <form onSubmit={handleSubmit} className="space-y-4">
            {dialog?.mode === "create" && (
              <div className="space-y-2">
                <Label htmlFor="tier-name">Name</Label>
                <Input
                  id="tier-name"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="basic"
                  required
                />
                <p className="text-xs text-muted-foreground">
                  Lowercase identifier (used in APIs and seed data).
                </p>
              </div>
            )}

            <div className="space-y-2">
              <Label htmlFor="tier-display-name">Display Name</Label>
              <Input
                id="tier-display-name"
                value={displayName}
                onChange={(e) => setDisplayName(e.target.value)}
                placeholder="Basic"
                required
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="tier-description">Description</Label>
              <Textarea
                id="tier-description"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="Describe what this tier enables..."
              />
            </div>

            <fieldset className="space-y-3 rounded-md border p-4">
              <legend className="px-1 text-sm font-medium">Features</legend>
              <div className="grid gap-3 md:grid-cols-2">
                {KNOWN_FEATURES.map((f) => (
                  <div key={f} className="flex items-center justify-between gap-3">
                    <Label className="font-mono text-xs">{f}</Label>
                    <Switch checked={!!features[f]} onCheckedChange={(v) => setFeature(f, v)} />
                  </div>
                ))}
              </div>
            </fieldset>

            <div className="grid gap-4 md:grid-cols-2">
              <div className="space-y-2">
                <Label htmlFor="tier-sort-order">Sort Order</Label>
                <Input
                  id="tier-sort-order"
                  type="number"
                  value={sortOrder}
                  onChange={(e) => setSortOrder(e.target.value)}
                />
              </div>
              {dialog?.mode === "edit" && (
                <div className="flex items-center justify-between rounded-md border p-3">
                  <div className="space-y-0.5">
                    <div className="text-sm font-medium">Active</div>
                    <div className="text-xs text-muted-foreground">
                      Disable to hide tier from customers.
                    </div>
                  </div>
                  <Switch checked={isActive} onCheckedChange={setIsActive} />
                </div>
              )}
            </div>

            <div className="flex justify-end gap-2 pt-2">
              <Button type="button" variant="outline" onClick={() => setDialog(null)}>
                Cancel
              </Button>
              <Button
                type="submit"
                disabled={createMutation.isPending || updateMutation.isPending}
              >
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
        </DialogContent>
      </Dialog>
    </div>
  );
}

