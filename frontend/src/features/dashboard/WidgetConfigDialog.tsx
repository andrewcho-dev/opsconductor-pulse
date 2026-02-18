import { useState, useEffect } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
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
import { updateWidget } from "@/services/api/dashboards";
import { getWidgetDefinition } from "./widgets/widget-registry";
import type { DashboardWidget } from "@/services/api/dashboards";
import { toast } from "sonner";
import { getErrorMessage } from "@/lib/errors";

interface WidgetConfigDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  dashboardId: number;
  widget: DashboardWidget;
}

const TIME_RANGES = [
  { value: "1h", label: "Last 1 hour" },
  { value: "6h", label: "Last 6 hours" },
  { value: "24h", label: "Last 24 hours" },
  { value: "7d", label: "Last 7 days" },
  { value: "30d", label: "Last 30 days" },
];

const METRICS = [
  { value: "temperature", label: "Temperature" },
  { value: "humidity", label: "Humidity" },
  { value: "pressure", label: "Pressure" },
  { value: "vibration", label: "Vibration" },
  { value: "power", label: "Power" },
  { value: "flow", label: "Flow" },
  { value: "level", label: "Level" },
  { value: "device_count", label: "Device Count" },
  { value: "alert_count", label: "Alert Count" },
  { value: "uptime_pct", label: "Uptime %" },
];

export function WidgetConfigDialog({
  open,
  onOpenChange,
  dashboardId,
  widget,
}: WidgetConfigDialogProps) {
  const [title, setTitle] = useState(widget.title);
  const [config, setConfig] = useState<Record<string, unknown>>(widget.config);
  const queryClient = useQueryClient();
  const definition = getWidgetDefinition(widget.widget_type);

  useEffect(() => {
    setTitle(widget.title);
    setConfig(widget.config);
  }, [widget]);

  const mutation = useMutation({
    mutationFn: () => updateWidget(dashboardId, widget.id, { title, config }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["dashboard", dashboardId] });
      onOpenChange(false);
      toast.success("Widget updated");
    },
    onError: (err: Error) => {
      toast.error(getErrorMessage(err) || "Failed to update widget");
    },
  });

  function updateConfig(key: string, value: unknown) {
    setConfig((prev) => ({ ...prev, [key]: value }));
  }

  function renderConfigFields() {
    const widgetType = widget.widget_type;

    if (widgetType === "kpi_tile" || widgetType === "line_chart" || widgetType === "bar_chart") {
      return (
        <>
          <div className="space-y-2">
            <Label>Metric</Label>
            <Select
              value={(config.metric as string) || ""}
              onValueChange={(v) => updateConfig("metric", v)}
            >
              <SelectTrigger>
                <SelectValue placeholder="Select metric" />
              </SelectTrigger>
              <SelectContent>
                {METRICS.map((m) => (
                  <SelectItem key={m.value} value={m.value}>
                    {m.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-2">
            <Label>Time Range</Label>
            <Select
              value={(config.time_range as string) || "24h"}
              onValueChange={(v) => updateConfig("time_range", v)}
            >
              <SelectTrigger>
                <SelectValue placeholder="Select range" />
              </SelectTrigger>
              <SelectContent>
                {TIME_RANGES.map((r) => (
                  <SelectItem key={r.value} value={r.value}>
                    {r.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </>
      );
    }

    if (widgetType === "gauge") {
      return (
        <>
          <div className="space-y-2">
            <Label>Metric</Label>
            <Select
              value={(config.metric as string) || "uptime_pct"}
              onValueChange={(v) => updateConfig("metric", v)}
            >
              <SelectTrigger>
                <SelectValue placeholder="Select metric" />
              </SelectTrigger>
              <SelectContent>
                {METRICS.map((m) => (
                  <SelectItem key={m.value} value={m.value}>
                    {m.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label>Min</Label>
              <Input
                type="number"
                value={(config.min as number) ?? 0}
                onChange={(e) => updateConfig("min", Number(e.target.value))}
              />
            </div>
            <div className="space-y-2">
              <Label>Max</Label>
              <Input
                type="number"
                value={(config.max as number) ?? 100}
                onChange={(e) => updateConfig("max", Number(e.target.value))}
              />
            </div>
          </div>
        </>
      );
    }

    if (widgetType === "table") {
      return (
        <div className="space-y-2">
          <Label>Rows to show</Label>
          <Input
            type="number"
            min={5}
            max={50}
            value={(config.limit as number) ?? 10}
            onChange={(e) => updateConfig("limit", Number(e.target.value))}
          />
        </div>
      );
    }

    if (widgetType === "alert_feed") {
      return (
        <div className="space-y-2">
          <Label>Max items</Label>
          <Input
            type="number"
            min={5}
            max={50}
            value={(config.max_items as number) ?? 20}
            onChange={(e) => updateConfig("max_items", Number(e.target.value))}
          />
        </div>
      );
    }

    return (
      <p className="text-sm text-muted-foreground">
        This widget type has no additional configuration.
      </p>
    );
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[480px]">
        <DialogHeader>
          <DialogTitle>Configure {definition?.label || "Widget"}</DialogTitle>
        </DialogHeader>

        <div className="space-y-4 py-4">
          <div className="space-y-2">
            <Label>Title</Label>
            <Input
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="Widget title"
              maxLength={100}
            />
          </div>
          {renderConfigFields()}
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button onClick={() => mutation.mutate()} disabled={mutation.isPending}>
            {mutation.isPending ? "Saving..." : "Save"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

