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
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import type { NormalizedMetricReference } from "@/services/api/types";
import { useCreateMetricMapping } from "@/hooks/use-metrics";
import { ApiError } from "@/services/api/client";

interface MapMetricDialogProps {
  open: boolean;
  rawMetric: string | null;
  normalizedMetrics: NormalizedMetricReference[];
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

function formatPreview(rawValue: number, multiplier: number, offset: number) {
  const normalized = rawValue * multiplier + offset;
  return `${rawValue} → ${Number.isFinite(normalized) ? normalized.toFixed(2) : "—"}`;
}

export default function MapMetricDialog({
  open,
  rawMetric,
  normalizedMetrics,
  onClose,
}: MapMetricDialogProps) {
  const mappingMutation = useCreateMetricMapping();
  const [normalizedName, setNormalizedName] = useState("");
  const [multiplier, setMultiplier] = useState("1");
  const [offset, setOffset] = useState("0");
  const [error, setError] = useState("");

  useEffect(() => {
    if (!open) return;
    setNormalizedName(normalizedMetrics[0]?.name || "");
    setMultiplier("1");
    setOffset("0");
    setError("");
  }, [open, normalizedMetrics]);

  const previewText = useMemo(() => {
    const mult = Number(multiplier);
    const off = Number(offset);
    if (!Number.isFinite(mult) || !Number.isFinite(off)) return "25 → —";
    return formatPreview(25, mult, off);
  }, [multiplier, offset]);

  async function handleSave() {
    if (!rawMetric) return;
    if (!normalizedName) {
      setError("Select a normalized metric.");
      return;
    }
    const mult = Number(multiplier);
    const off = Number(offset);
    if (!Number.isFinite(mult)) {
      setError("Multiplier must be a number.");
      return;
    }
    if (!Number.isFinite(off)) {
      setError("Offset must be a number.");
      return;
    }

    try {
      await mappingMutation.mutateAsync({
        raw_metric: rawMetric,
        normalized_name: normalizedName,
        multiplier: mult,
        offset_value: off,
      });
      onClose();
    } catch (err) {
      console.error("Failed to map metric:", err);
      setError(formatError(err));
    }
  }

  return (
    <Dialog open={open} onOpenChange={(next) => !next && onClose()}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>
            {rawMetric ? `Map "${rawMetric}" to Normalized Metric` : "Map Raw Metric"}
          </DialogTitle>
        </DialogHeader>
        <div className="space-y-4">
          {normalizedMetrics.length === 0 ? (
            <div className="text-sm text-muted-foreground">
              Create a normalized metric first.
            </div>
          ) : (
            <>
              <div className="grid gap-2">
                <Label>Target</Label>
                <Select value={normalizedName} onValueChange={setNormalizedName}>
                  <SelectTrigger className="w-full">
                    <SelectValue placeholder="Select normalized metric" />
                  </SelectTrigger>
                  <SelectContent>
                    {normalizedMetrics.map((metric) => (
                      <SelectItem key={metric.name} value={metric.name}>
                        {metric.name}
                        {metric.display_unit ? ` (${metric.display_unit})` : ""}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div className="rounded-md border border-border p-3 space-y-3">
                <div className="text-sm font-medium">
                  Formula: normalized = raw × M + O
                </div>
                <div className="grid gap-2 sm:grid-cols-2">
                  <div className="grid gap-2">
                    <Label htmlFor="map-multiplier">Multiplier (M)</Label>
                    <Input
                      id="map-multiplier"
                      value={multiplier}
                      onChange={(event) => setMultiplier(event.target.value)}
                      placeholder="1.8"
                    />
                  </div>
                  <div className="grid gap-2">
                    <Label htmlFor="map-offset">Offset (O)</Label>
                    <Input
                      id="map-offset"
                      value={offset}
                      onChange={(event) => setOffset(event.target.value)}
                      placeholder="32"
                    />
                  </div>
                </div>
                <div className="text-xs text-muted-foreground">Preview: {previewText}</div>
              </div>

              <div className="space-y-2">
                <Label>Common conversions</Label>
                <div className="flex flex-wrap gap-2">
                  <Button
                    type="button"
                    size="sm"
                    variant="outline"
                    onClick={() => {
                      setMultiplier("1.8");
                      setOffset("32");
                    }}
                  >
                    C→F
                  </Button>
                  <Button
                    type="button"
                    size="sm"
                    variant="outline"
                    onClick={() => {
                      setMultiplier("0.5556");
                      setOffset("-17.78");
                    }}
                  >
                    F→C
                  </Button>
                  <Button
                    type="button"
                    size="sm"
                    variant="outline"
                    onClick={() => {
                      setMultiplier("0.0689");
                      setOffset("0");
                    }}
                  >
                    PSI→Bar
                  </Button>
                  <Button
                    type="button"
                    size="sm"
                    variant="outline"
                    onClick={() => {
                      setMultiplier("1");
                      setOffset("0");
                    }}
                  >
                    None
                  </Button>
                </div>
              </div>
            </>
          )}
          {error && <p className="text-xs text-destructive">{error}</p>}
        </div>
        <DialogFooter>
          <Button type="button" variant="ghost" onClick={onClose}>
            Cancel
          </Button>
          <Button
            type="button"
            onClick={handleSave}
            disabled={!rawMetric || normalizedMetrics.length === 0 || mappingMutation.isPending}
          >
            Save Mapping
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
