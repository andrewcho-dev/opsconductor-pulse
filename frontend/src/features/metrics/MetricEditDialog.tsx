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
import type { MetricReference } from "@/services/api/types";
import { useDeleteMetricCatalog, useUpdateMetricCatalog } from "@/hooks/use-metrics";
import { ApiError } from "@/services/api/client";

interface MetricEditDialogProps {
  open: boolean;
  metric: MetricReference | null;
  onClose: () => void;
  canEdit: boolean;
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

function parseRange(range: string | null): { min: string; max: string } {
  if (!range) return { min: "", max: "" };
  const parts = range.split("-");
  if (parts.length !== 2) return { min: "", max: "" };
  return { min: parts[0].trim(), max: parts[1].trim() };
}

export default function MetricEditDialog({
  open,
  metric,
  onClose,
  canEdit,
}: MetricEditDialogProps) {
  const updateMutation = useUpdateMetricCatalog();
  const deleteMutation = useDeleteMetricCatalog();
  const [description, setDescription] = useState("");
  const [unit, setUnit] = useState("");
  const [minValue, setMinValue] = useState("");
  const [maxValue, setMaxValue] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    if (!open || !metric) return;
    setDescription(metric.description ?? "");
    setUnit(metric.unit ?? "");
    const { min, max } = parseRange(metric.range ?? null);
    setMinValue(min);
    setMaxValue(max);
    setError("");
  }, [open, metric]);

  const canClear = useMemo(() => {
    return Boolean(metric?.description || metric?.unit || metric?.range);
  }, [metric]);

  async function handleSave() {
    if (!metric) return;
    setError("");
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
      await updateMutation.mutateAsync({
        metric_name: metric.name,
        description: description.trim() || null,
        unit: unit.trim() || null,
        expected_min: expectedMin,
        expected_max: expectedMax,
      });
      onClose();
    } catch (err) {
      setError(formatError(err));
    }
  }

  async function handleClear() {
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
          <DialogTitle>Edit Metric: {metric?.name || "—"}</DialogTitle>
        </DialogHeader>
        <div className="space-y-4">
          <div className="grid gap-2">
            <Label htmlFor="metric-edit-description">Description</Label>
            <Input
              id="metric-edit-description"
              value={description}
              onChange={(event) => setDescription(event.target.value)}
              placeholder="Temperature sensor reading"
              disabled={!canEdit}
            />
          </div>
          <div className="grid gap-2">
            <Label htmlFor="metric-edit-unit">Unit</Label>
            <Input
              id="metric-edit-unit"
              value={unit}
              onChange={(event) => setUnit(event.target.value)}
              placeholder="°C"
              disabled={!canEdit}
            />
          </div>
          <div className="grid gap-2">
            <Label>Expected Range</Label>
            <div className="flex items-center gap-2">
              <Input
                value={minValue}
                onChange={(event) => setMinValue(event.target.value)}
                placeholder="Min"
                disabled={!canEdit}
              />
              <span className="text-xs text-muted-foreground">to</span>
              <Input
                value={maxValue}
                onChange={(event) => setMaxValue(event.target.value)}
                placeholder="Max"
                disabled={!canEdit}
              />
            </div>
          </div>
          {error && <p className="text-xs text-destructive">{error}</p>}
        </div>
        <DialogFooter className="justify-between">
          <Button
            type="button"
            variant="outline"
            onClick={handleClear}
            disabled={!canEdit || !canClear || deleteMutation.isPending}
          >
            Clear
          </Button>
          <div className="flex gap-2">
            <Button type="button" variant="ghost" onClick={onClose}>
              Cancel
            </Button>
            <Button
              type="button"
              onClick={handleSave}
              disabled={!canEdit || updateMutation.isPending}
            >
              Save
            </Button>
          </div>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
