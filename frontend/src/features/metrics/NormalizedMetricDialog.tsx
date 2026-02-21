import { useEffect, useMemo, useState } from "react";
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import type { NormalizedMetricReference } from "@/services/api/types";
import {
  useCreateMetricMapping,
  useDeleteMetricMapping,
  useMetricMappings,
  useUpdateMetricMapping,
} from "@/hooks/use-metrics";
import MappingEditRow from "./MappingEditRow";
import {
  useCreateNormalizedMetric,
  useDeleteNormalizedMetric,
  useUpdateNormalizedMetric,
} from "@/hooks/use-metrics";
import { toast } from "sonner";
import { getErrorMessage } from "@/lib/errors";

// DataTable not used: Small configuration table within a dialog.
// DataTable would add unnecessary complexity for a few-row config display.

interface NormalizedMetricDialogProps {
  open: boolean;
  metric: NormalizedMetricReference | null;
  onClose: () => void;
}

export default function NormalizedMetricDialog({
  open,
  metric,
  onClose,
}: NormalizedMetricDialogProps) {
  const createMutation = useCreateNormalizedMetric();
  const updateMutation = useUpdateNormalizedMetric();
  const deleteMutation = useDeleteNormalizedMetric();
  const createMapping = useCreateMetricMapping();
  const updateMapping = useUpdateMetricMapping();
  const deleteMapping = useDeleteMetricMapping();
  const isEditing = !!metric;
  const { data: mappingsData } = useMetricMappings(metric?.name);

  const [name, setName] = useState("");
  const [unit, setUnit] = useState("");
  const [description, setDescription] = useState("");
  const [minValue, setMinValue] = useState("");
  const [maxValue, setMaxValue] = useState("");
  const [error, setError] = useState("");
  const [showAddMap, setShowAddMap] = useState(false);
  const [newRawMetric, setNewRawMetric] = useState("");
  const [newMultiplier, setNewMultiplier] = useState("1");
  const [newOffset, setNewOffset] = useState("0");

  useEffect(() => {
    if (!open) return;
    if (metric) {
      setName(metric.name);
      setUnit(metric.display_unit ?? "");
      setDescription(metric.description ?? "");
      setMinValue(metric.expected_min != null ? String(metric.expected_min) : "");
      setMaxValue(metric.expected_max != null ? String(metric.expected_max) : "");
    } else {
      setName("");
      setUnit("");
      setDescription("");
      setMinValue("");
      setMaxValue("");
    }
    setShowAddMap(false);
    setNewRawMetric("");
    setNewMultiplier("1");
    setNewOffset("0");
    setError("");
  }, [open, metric]);

  const canDelete = useMemo(() => isEditing, [isEditing]);
  const isSaving = createMutation.isPending || updateMutation.isPending;

  async function handleSave() {
    setError("");
    const normalizedName = name.trim();
    if (!normalizedName) {
      setError("Name is required.");
      return;
    }
    const normalizedMin = minValue.trim();
    const normalizedMax = maxValue.trim();
    const expectedMin = normalizedMin ? Number(normalizedMin) : null;
    const expectedMax = normalizedMax ? Number(normalizedMax) : null;
    if (normalizedMin && Number.isNaN(expectedMin)) {
      setError("Expected minimum must be a number.");
      return;
    }
    if (normalizedMax && Number.isNaN(expectedMax)) {
      setError("Expected maximum must be a number.");
      return;
    }
    if (
      expectedMin !== null &&
      expectedMax !== null &&
      expectedMin > expectedMax
    ) {
      setError("Expected minimum must be less than or equal to maximum.");
      return;
    }

    try {
      if (isEditing) {
        await updateMutation.mutateAsync({
          name: normalizedName,
          payload: {
            display_unit: unit.trim() || null,
            description: description.trim() || null,
            expected_min: expectedMin,
            expected_max: expectedMax,
          },
        });
      } else {
        await createMutation.mutateAsync({
          normalized_name: normalizedName,
          display_unit: unit.trim() || null,
          description: description.trim() || null,
          expected_min: expectedMin,
          expected_max: expectedMax,
        });
      }
      toast.success(isEditing ? "Normalized metric updated" : "Normalized metric created");
      onClose();
    } catch (err) {
      toast.error(getErrorMessage(err) || "Failed to save normalized metric");
      setError(getErrorMessage(err));
    }
  }

  async function handleDelete() {
    if (!metric) return;
    setError("");
    try {
      await deleteMutation.mutateAsync(metric.name);
      toast.success("Normalized metric deleted");
      onClose();
    } catch (err) {
      toast.error(getErrorMessage(err) || "Failed to delete normalized metric");
      setError(getErrorMessage(err));
    }
  }

  return (
    <Dialog open={open} onOpenChange={(next) => !next && onClose()}>
      <DialogContent className="sm:max-w-2xl">
        <DialogHeader>
          <DialogTitle>
            {isEditing
              ? `Edit Normalized Metric: ${metric?.name}`
              : `Create Normalized Metric`}
          </DialogTitle>
        </DialogHeader>
        <div className="space-y-4">
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="grid gap-2">
              <Label htmlFor="normalized-name">Name (used in rules)</Label>
              <Input
                id="normalized-name"
                value={name}
                onChange={(event) => setName(event.target.value)}
                placeholder="Temperature"
                disabled={isEditing}
              />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="normalized-unit">Display Unit</Label>
              <Input
                id="normalized-unit"
                value={unit}
                onChange={(event) => setUnit(event.target.value)}
                placeholder="°F"
              />
            </div>
          </div>
          <div className="grid gap-2">
            <Label htmlFor="normalized-description">Description</Label>
            <Input
              id="normalized-description"
              value={description}
              onChange={(event) => setDescription(event.target.value)}
              placeholder="Temperature reading"
            />
          </div>
          <div className="grid gap-2">
            <Label>Expected Range (optional)</Label>
            <div className="flex items-center gap-2">
              <Input
                value={minValue}
                onChange={(event) => setMinValue(event.target.value)}
                placeholder="Min"
              />
              <span className="text-sm text-muted-foreground">to</span>
              <Input
                value={maxValue}
                onChange={(event) => setMaxValue(event.target.value)}
                placeholder="Max"
              />
            </div>
          </div>
          {isEditing && (
            <div className="space-y-3 border-t border-border pt-4">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div className="text-sm font-semibold">Mapped Raw Metrics</div>
                <Button size="sm" variant="outline" onClick={() => setShowAddMap(true)}>
                  + Add Map
                </Button>
              </div>
              {mappingsData?.mappings?.length ? (
                <div className="rounded-md border border-border">
                  <table className="w-full text-sm">
                    <thead className="border-b border-border bg-muted/40 text-left">
                      <tr>
                        <th className="px-3 py-2">Raw Metric</th>
                        <th className="px-3 py-2">Multiplier</th>
                        <th className="px-3 py-2">Offset</th>
                        <th className="px-3 py-2 text-right">Actions</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-border">
                      {mappingsData.mappings.map((mapping) => (
                        <MappingEditRow
                          key={mapping.raw_metric}
                          rawMetric={mapping.raw_metric}
                          multiplier={mapping.multiplier ?? 1}
                          offset={mapping.offset_value ?? 0}
                          onSave={(payload) =>
                            updateMapping.mutateAsync({
                              rawMetric: mapping.raw_metric,
                              payload,
                            })
                          }
                          onRemove={() => deleteMapping.mutateAsync(mapping.raw_metric)}
                          isSaving={updateMapping.isPending || deleteMapping.isPending}
                        />
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <div className="text-sm text-muted-foreground">
                  No raw metrics mapped yet.
                </div>
              )}

              {showAddMap && (
                <div className="rounded-md border border-border p-3 space-y-3">
                  <div className="text-sm font-medium">Add Mapping</div>
                  <div className="grid gap-2">
                    <Label htmlFor="new-raw-metric">Raw Metric</Label>
                    <Input
                      id="new-raw-metric"
                      value={newRawMetric}
                      onChange={(event) => setNewRawMetric(event.target.value)}
                      placeholder="temp_c"
                    />
                  </div>
                  <div className="grid gap-2 sm:grid-cols-2">
                    <div className="grid gap-2">
                      <Label htmlFor="new-multiplier">Multiplier</Label>
                      <Input
                        id="new-multiplier"
                        value={newMultiplier}
                        onChange={(event) => setNewMultiplier(event.target.value)}
                        placeholder="1.8"
                      />
                    </div>
                    <div className="grid gap-2">
                      <Label htmlFor="new-offset">Offset</Label>
                      <Input
                        id="new-offset"
                        value={newOffset}
                        onChange={(event) => setNewOffset(event.target.value)}
                        placeholder="32"
                      />
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <Button
                      size="sm"
                      onClick={async () => {
                        const mult = Number(newMultiplier);
                        const off = Number(newOffset);
                        if (!newRawMetric.trim()) return;
                        await createMapping.mutateAsync({
                          raw_metric: newRawMetric.trim(),
                          normalized_name: metric?.name || name.trim(),
                          multiplier: Number.isNaN(mult) ? 1 : mult,
                          offset_value: Number.isNaN(off) ? 0 : off,
                        });
                        setShowAddMap(false);
                        setNewRawMetric("");
                        setNewMultiplier("1");
                        setNewOffset("0");
                      }}
                      disabled={createMapping.isPending}
                    >
                      Add
                    </Button>
                    <Button size="sm" variant="ghost" onClick={() => setShowAddMap(false)}>
                      Cancel
                    </Button>
                  </div>
                </div>
              )}
            </div>
          )}

          {error && <p className="text-sm text-destructive">{error}</p>}
        </div>
        <DialogFooter className="justify-between">
          <Button
            type="button"
            variant="outline"
            onClick={handleDelete}
            disabled={!canDelete || deleteMutation.isPending}
          >
            Delete
          </Button>
          <div className="flex gap-2">
            <Button type="button" variant="ghost" onClick={onClose}>
              Cancel
            </Button>
            <Button type="button" onClick={handleSave} disabled={isSaving}>
              {isEditing ? "Save" : "Create"}
            </Button>
          </div>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
