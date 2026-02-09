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
  useCreateNormalizedMetric,
  useDeleteNormalizedMetric,
  useUpdateNormalizedMetric,
} from "@/hooks/use-metrics";
import { ApiError } from "@/services/api/client";

interface NormalizedMetricDialogProps {
  open: boolean;
  metric: NormalizedMetricReference | null;
  onClose: () => void;
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

export default function NormalizedMetricDialog({
  open,
  metric,
  onClose,
}: NormalizedMetricDialogProps) {
  const createMutation = useCreateNormalizedMetric();
  const updateMutation = useUpdateNormalizedMetric();
  const deleteMutation = useDeleteNormalizedMetric();
  const isEditing = !!metric;

  const [name, setName] = useState("");
  const [unit, setUnit] = useState("");
  const [description, setDescription] = useState("");
  const [minValue, setMinValue] = useState("");
  const [maxValue, setMaxValue] = useState("");
  const [error, setError] = useState("");

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
      onClose();
    } catch (err) {
      setError(formatError(err));
    }
  }

  async function handleDelete() {
    if (!metric) return;
    setError("");
    try {
      await deleteMutation.mutateAsync(metric.name);
      onClose();
    } catch (err) {
      setError(formatError(err));
    }
  }

  return (
    <Dialog open={open} onOpenChange={(next) => !next && onClose()}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>
            {isEditing ? `Edit Normalized Metric` : `Create Normalized Metric`}
          </DialogTitle>
        </DialogHeader>
        <div className="space-y-4">
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
              <span className="text-xs text-muted-foreground">to</span>
              <Input
                value={maxValue}
                onChange={(event) => setMaxValue(event.target.value)}
                placeholder="Max"
              />
            </div>
          </div>
          {error && <p className="text-xs text-destructive">{error}</p>}
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
