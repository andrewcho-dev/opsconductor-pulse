import { useState, useEffect } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
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
import { Switch } from "@/components/ui/switch";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { ScrollArea } from "@/components/ui/scroll-area";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { updateWidget } from "@/services/api/dashboards";
import { DISPLAY_OPTIONS, getWidgetDefinition } from "./widgets/widget-registry";
import type { DashboardWidget } from "@/services/api/dashboards";
import { toast } from "sonner";
import { getErrorMessage } from "@/lib/errors";
import { Plus, X } from "lucide-react";
import { useDevices } from "@/hooks/use-devices";
import { listDeviceSensors } from "@/services/api/sensors";

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
  const { data: devicesData, isLoading: devicesLoading } = useDevices({ limit: 200, offset: 0 });
  const devices = devicesData?.devices ?? [];
  const selectedDeviceId =
    Array.isArray(config.devices) && (config.devices as string[]).length > 0
      ? (config.devices as string[])[0]
      : undefined;

  const { data: sensorsData } = useQuery({
    queryKey: ["device-sensors", selectedDeviceId],
    queryFn: () => listDeviceSensors(selectedDeviceId!),
    enabled: !!selectedDeviceId,
  });

  const widgetType = widget.widget_type;

  // Widgets complex enough to need tabs
  const needsTabs = [
    "line_chart",
    "bar_chart",
    "area_chart",
    "scatter",
    "radar",
    "kpi_tile",
    "stat_card",
    "gauge",
    "pie_chart",
  ].includes(widgetType);

  // Widgets that support thresholds
  const hasThresholds = [
    "kpi_tile",
    "line_chart",
    "bar_chart",
    "area_chart",
    "scatter",
    "gauge",
    "stat_card",
    "health_score",
    "device_count",
  ].includes(widgetType);

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
    if (
      widgetType === "fleet_overview" ||
      widgetType === "device_count" ||
      widgetType === "fleet_status" ||
      widgetType === "health_score"
    ) {
      return (
        <div className="space-y-2">
          <p className="text-sm text-muted-foreground">
            Fleet Overview is a composite widget. Configure thresholds below to control health coloring.
          </p>
          {renderThresholdsTab()}
        </div>
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

  function renderDataTab() {
    const statusDotClass = (status: string | undefined) => {
      if (status === "ONLINE") return "bg-status-online";
      if (status === "STALE") return "bg-status-warning";
      if (status === "OFFLINE") return "bg-status-critical";
      return "bg-muted-foreground";
    };

    const displayAsSection = DISPLAY_OPTIONS[widgetType] ? (
      <div className="space-y-2">
        <Label htmlFor="display_as">Display As</Label>
        <Select
          value={(config.display_as as string) ?? DISPLAY_OPTIONS[widgetType][0].value}
          onValueChange={(v) => updateConfig("display_as", v)}
        >
          <SelectTrigger id="display_as">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {DISPLAY_OPTIONS[widgetType].map((opt) => (
              <SelectItem key={opt.value} value={opt.value}>
                {opt.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>
    ) : null;

    const deviceSection = ["line_chart", "bar_chart", "area_chart"].includes(widgetType) ? (
      <div className="space-y-2">
        <Label>Device</Label>
        <Select
          value={
            Array.isArray(config.devices) && (config.devices as string[]).length > 0
              ? (config.devices as string[])[0]
              : ""
          }
          onValueChange={(v) => updateConfig("devices", v ? [v] : [])}
          disabled={devicesLoading || devices.length === 0}
        >
          <SelectTrigger>
            <SelectValue
              placeholder={
                devicesLoading ? "Loading..." : devices.length === 0 ? "No devices" : "Select device"
              }
            />
          </SelectTrigger>
          <SelectContent>
            {devices.map((d) => (
              <SelectItem key={d.device_id} value={d.device_id}>
                <span className="flex items-center gap-2">
                  <span className={`h-2 w-2 rounded-full ${statusDotClass(d.status)}`} />
                  <span>{d.device_id}</span>
                </span>
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>
    ) : null;

    const sensorMetrics = sensorsData?.sensors ?? [];
    const hasSensorMetrics = sensorMetrics.length > 0;

    const metricSelect = (
      <div className="space-y-2">
        <Label>Sensor / Metric</Label>
        <Select value={(config.metric as string) || ""} onValueChange={(v) => updateConfig("metric", v)}>
          <SelectTrigger>
            <SelectValue
              placeholder={
                !selectedDeviceId
                  ? "Select a device first"
                  : hasSensorMetrics
                    ? "Select a sensor"
                    : "Select metric"
              }
            />
          </SelectTrigger>
          <SelectContent>
            {hasSensorMetrics
              ? sensorMetrics.map((s) => (
                  <SelectItem key={s.sensor_id ?? s.id} value={s.metric_name ?? s.metric_key}>
                    <span className="flex items-center justify-between gap-2">
                      <span>{s.label || s.metric_name || s.metric_key}</span>
                      <span className="text-xs text-muted-foreground">
                        ({s.sensor_type}
                        {s.unit ? `, ${s.unit}` : ""})
                      </span>
                    </span>
                  </SelectItem>
                ))
              : METRICS.map((m) => (
                  <SelectItem key={m.value} value={m.value}>
                    {m.label}
                  </SelectItem>
                ))}
          </SelectContent>
        </Select>
      </div>
    );

    if (["line_chart", "bar_chart", "area_chart"].includes(widgetType)) {
      return (
        <>
          {displayAsSection}
          {deviceSection}
          <div className="grid grid-cols-2 gap-3">
            {metricSelect}
            <div className="space-y-2">
              <Label>Time Range</Label>
              <Select
                value={(config.time_range as string) || "24h"}
                onValueChange={(v) => updateConfig("time_range", v)}
              >
                <SelectTrigger>
                  <SelectValue />
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
          </div>
        </>
      );
    }

    if (widgetType === "kpi_tile") {
      return (
        <>
          {displayAsSection}
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
        </>
      );
    }

    if (widgetType === "stat_card") {
      const sparklineDevice =
        typeof config.sparkline_device === "string" ? config.sparkline_device : "none";
      return (
        <>
          {displayAsSection}
          <div className="space-y-2">
            <Label>Metric</Label>
            <Select
              value={(config.metric as string) || "device_count"}
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
            <Label>Sparkline Device</Label>
            <Select
              value={sparklineDevice}
              onValueChange={(v) =>
                updateConfig("sparkline_device", v === "none" ? undefined : v)
              }
              disabled={devicesLoading || devices.length === 0}
            >
              <SelectTrigger>
                <SelectValue placeholder="None" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="none">None</SelectItem>
                {devices.map((d) => (
                  <SelectItem key={d.device_id} value={d.device_id}>
                    <span className="flex items-center gap-2">
                      <span className={`h-2 w-2 rounded-full ${statusDotClass(d.status)}`} />
                      <span>{d.device_id}</span>
                    </span>
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
          {displayAsSection}
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-2">
              <Label>Metric</Label>
              <Select
                value={(config.metric as string) || "uptime_pct"}
                onValueChange={(v) => updateConfig("metric", v)}
              >
                <SelectTrigger>
                  <SelectValue />
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
              <Label>Gauge Style</Label>
              <Select
                value={(config.gauge_style as string) ?? "arc"}
                onValueChange={(v) => updateConfig("gauge_style", v)}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="arc">Progress Arc</SelectItem>
                  <SelectItem value="speedometer">Speedometer</SelectItem>
                  <SelectItem value="ring">Ring</SelectItem>
                  <SelectItem value="grade">Grade Bands</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
          <div className="grid grid-cols-2 gap-3">
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

    if (widgetType === "pie_chart") {
      return (
        <>
          <div className="space-y-2">
            <Label>Data Source</Label>
            <Select
              value={(config.pie_data_source as string) ?? "fleet_status"}
              onValueChange={(v) => updateConfig("pie_data_source", v)}
            >
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="fleet_status">Fleet Status</SelectItem>
                <SelectItem value="alert_severity">Alert Severity</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div className="grid grid-cols-2 gap-x-6 gap-y-2">
            <div className="flex items-center justify-between">
              <Label htmlFor="doughnut">Donut Style</Label>
              <Switch
                id="doughnut"
                checked={(config.doughnut as boolean | undefined) ?? true}
                onCheckedChange={(c) => updateConfig("doughnut", c)}
              />
            </div>
            <div className="flex items-center justify-between">
              <Label htmlFor="show_labels">Show Labels</Label>
              <Switch
                id="show_labels"
                checked={(config.show_labels as boolean | undefined) ?? true}
                onCheckedChange={(c) => updateConfig("show_labels", c)}
              />
            </div>
          </div>
        </>
      );
    }

    if (widgetType === "scatter") {
      return (
        <>
          <div className="space-y-2">
            <Label>Device</Label>
            <Select
              value={
                Array.isArray(config.devices) && (config.devices as string[]).length > 0
                  ? (config.devices as string[])[0]
                  : ""
              }
              onValueChange={(v) => updateConfig("devices", v ? [v] : [])}
              disabled={devicesLoading || devices.length === 0}
            >
              <SelectTrigger>
                <SelectValue
                  placeholder={
                    devicesLoading ? "Loading..." : devices.length === 0 ? "No devices" : "Select device"
                  }
                />
              </SelectTrigger>
              <SelectContent>
                {devices.map((d) => (
                  <SelectItem key={d.device_id} value={d.device_id}>
                    <span className="flex items-center gap-2">
                      <span className={`h-2 w-2 rounded-full ${statusDotClass(d.status)}`} />
                      <span>{d.device_id}</span>
                    </span>
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-2">
              <Label>X Axis Sensor</Label>
              <Select
                value={(config.x_metric as string) || "temperature"}
                onValueChange={(v) => updateConfig("x_metric", v)}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {hasSensorMetrics
                    ? sensorMetrics.map((s) => (
                        <SelectItem key={s.sensor_id ?? s.id} value={s.metric_name ?? s.metric_key}>
                          {s.label || s.metric_name || s.metric_key}
                        </SelectItem>
                      ))
                    : METRICS.map((m) => (
                        <SelectItem key={m.value} value={m.value}>
                          {m.label}
                        </SelectItem>
                      ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label>Y Axis Sensor</Label>
              <Select
                value={(config.y_metric as string) || "humidity"}
                onValueChange={(v) => updateConfig("y_metric", v)}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {hasSensorMetrics
                    ? sensorMetrics.map((s) => (
                        <SelectItem key={s.sensor_id ?? s.id} value={s.metric_name ?? s.metric_key}>
                          {s.label || s.metric_name || s.metric_key}
                        </SelectItem>
                      ))
                    : METRICS.map((m) => (
                        <SelectItem key={m.value} value={m.value}>
                          {m.label}
                        </SelectItem>
                      ))}
                </SelectContent>
              </Select>
            </div>
          </div>
          <div className="space-y-2">
            <Label>Time Range</Label>
            <Select
              value={(config.time_range as string) || "24h"}
              onValueChange={(v) => updateConfig("time_range", v)}
            >
              <SelectTrigger>
                <SelectValue />
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

    if (widgetType === "radar") {
      const selectedMetrics = Array.isArray(config.radar_metrics)
        ? (config.radar_metrics as string[])
        : hasSensorMetrics
          ? sensorMetrics.slice(0, 3).map((s) => s.metric_name)
          : ["temperature", "humidity", "pressure"];

      const radarOptions = hasSensorMetrics
        ? sensorMetrics.map((s) => ({
            value: s.metric_name,
            label: s.label || s.metric_name,
            meta: `${s.sensor_type}${s.unit ? `, ${s.unit}` : ""}`,
          }))
        : METRICS.map((m) => ({ value: m.value, label: m.label, meta: "" }));

      return (
        <>
          <div className="space-y-2">
            <Label>Device</Label>
            <Select
              value={
                Array.isArray(config.devices) && (config.devices as string[]).length > 0
                  ? (config.devices as string[])[0]
                  : ""
              }
              onValueChange={(v) => updateConfig("devices", v ? [v] : [])}
              disabled={devicesLoading || devices.length === 0}
            >
              <SelectTrigger>
                <SelectValue
                  placeholder={
                    devicesLoading ? "Loading..." : devices.length === 0 ? "No devices" : "Select device"
                  }
                />
              </SelectTrigger>
              <SelectContent>
                {devices.map((d) => (
                  <SelectItem key={d.device_id} value={d.device_id}>
                    <span className="flex items-center gap-2">
                      <span className={`h-2 w-2 rounded-full ${statusDotClass(d.status)}`} />
                      <span>{d.device_id}</span>
                    </span>
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-2">
            <Label>Metrics (select 3–6)</Label>
            <div className="grid grid-cols-2 gap-1 max-h-[180px] overflow-y-auto">
              {radarOptions.map((m) => {
                const isSelected = selectedMetrics.includes(m.value);
                const atLimit = selectedMetrics.length >= 6 && !isSelected;
                return (
                  <label
                    key={m.value}
                    className={`flex items-center gap-2 text-sm rounded px-2 py-1 cursor-pointer hover:bg-accent ${atLimit ? "opacity-50 cursor-not-allowed" : ""}`}
                  >
                    <input
                      type="checkbox"
                      checked={isSelected}
                      disabled={atLimit}
                      onChange={(e) => {
                        const newMetrics = e.target.checked
                          ? [...selectedMetrics, m.value]
                          : selectedMetrics.filter((x) => x !== m.value);
                        if (newMetrics.length >= 3) updateConfig("radar_metrics", newMetrics);
                      }}
                      className="rounded"
                    />
                    <span className="truncate">
                      {m.label}
                      {m.meta ? (
                        <span className="text-xs text-muted-foreground ml-1">({m.meta})</span>
                      ) : null}
                    </span>
                  </label>
                );
              })}
            </div>
            {selectedMetrics.length < 3 && (
              <p className="text-xs text-destructive">Select at least 3 metrics</p>
            )}
          </div>
          <div className="space-y-2">
            <Label>Time Range</Label>
            <Select
              value={(config.time_range as string) || "24h"}
              onValueChange={(v) => updateConfig("time_range", v)}
            >
              <SelectTrigger>
                <SelectValue />
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

    return null;
  }

  function renderStyleTab() {
    const isChart = ["line_chart", "bar_chart", "area_chart", "scatter", "radar", "pie_chart"].includes(
      widgetType
    );
    const supportsDecimalPrecision = [
      "kpi_tile",
      "gauge",
      "stat_card",
      "line_chart",
      "bar_chart",
      "area_chart",
    ].includes(widgetType);
    const supportsYBounds = ["line_chart", "bar_chart", "area_chart", "scatter"].includes(widgetType);
    const isLineArea = ["line_chart", "area_chart"].includes(widgetType);

    return (
      <>
        <div className="space-y-2">
          <h4 className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
            Visibility
          </h4>
          <div className="grid grid-cols-2 gap-x-6 gap-y-2">
            <div className="flex items-center justify-between">
              <Label htmlFor="show_title" className="text-sm">
                Title
              </Label>
              <Switch
                id="show_title"
                checked={(config.show_title as boolean | undefined) !== false}
                onCheckedChange={(c) => updateConfig("show_title", c)}
              />
            </div>
            {isChart && (
              <div className="flex items-center justify-between">
                <Label htmlFor="show_legend" className="text-sm">
                  Legend
                </Label>
                <Switch
                  id="show_legend"
                  checked={(config.show_legend as boolean | undefined) !== false}
                  onCheckedChange={(c) => updateConfig("show_legend", c)}
                />
              </div>
            )}
            {isChart && !["radar", "pie_chart"].includes(widgetType) && (
              <>
                <div className="flex items-center justify-between">
                  <Label htmlFor="show_x_axis" className="text-sm">
                    X Axis
                  </Label>
                  <Switch
                    id="show_x_axis"
                    checked={(config.show_x_axis as boolean | undefined) !== false}
                    onCheckedChange={(c) => updateConfig("show_x_axis", c)}
                  />
                </div>
                <div className="flex items-center justify-between">
                  <Label htmlFor="show_y_axis" className="text-sm">
                    Y Axis
                  </Label>
                  <Switch
                    id="show_y_axis"
                    checked={(config.show_y_axis as boolean | undefined) !== false}
                    onCheckedChange={(c) => updateConfig("show_y_axis", c)}
                  />
                </div>
              </>
            )}
          </div>
        </div>

        {(supportsDecimalPrecision || supportsYBounds) && (
          <div className="space-y-2">
            <h4 className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
              Formatting
            </h4>
            <div className="grid grid-cols-2 gap-3">
              {supportsDecimalPrecision ? (
                <div className="space-y-1">
                  <Label htmlFor="decimal_precision" className="text-sm">
                    Decimal Places
                  </Label>
                  <Input
                    id="decimal_precision"
                    type="number"
                    min={0}
                    max={4}
                    value={(config.decimal_precision as number) ?? 1}
                    onChange={(e) => updateConfig("decimal_precision", Number(e.target.value))}
                  />
                </div>
              ) : (
                <div />
              )}

              {supportsYBounds ? (
                <div className="space-y-1">
                  <Label htmlFor="y_axis_min" className="text-sm">
                    Y Axis Min
                  </Label>
                  <Input
                    id="y_axis_min"
                    type="number"
                    placeholder="Auto"
                    value={(config.y_axis_min as number | undefined) ?? ""}
                    onChange={(e) =>
                      updateConfig(
                        "y_axis_min",
                        e.target.value === "" ? undefined : Number(e.target.value)
                      )
                    }
                  />
                </div>
              ) : (
                <div />
              )}

              {supportsYBounds && (
                <div className="space-y-1">
                  <Label htmlFor="y_axis_max" className="text-sm">
                    Y Axis Max
                  </Label>
                  <Input
                    id="y_axis_max"
                    type="number"
                    placeholder="Auto"
                    value={(config.y_axis_max as number | undefined) ?? ""}
                    onChange={(e) =>
                      updateConfig(
                        "y_axis_max",
                        e.target.value === "" ? undefined : Number(e.target.value)
                      )
                    }
                  />
                </div>
              )}
            </div>
          </div>
        )}

        {(isLineArea || widgetType === "bar_chart") && (
          <div className="space-y-2">
            <h4 className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
              Chart Options
            </h4>
            <div className="grid grid-cols-2 gap-x-6 gap-y-2">
              {isLineArea && (
                <>
                  <div className="flex items-center justify-between">
                    <Label htmlFor="smooth" className="text-sm">
                      Smooth
                    </Label>
                    <Switch
                      id="smooth"
                      checked={(config.smooth as boolean | undefined) ?? true}
                      onCheckedChange={(c) => updateConfig("smooth", c)}
                    />
                  </div>
                  <div className="flex items-center justify-between">
                    <Label htmlFor="step" className="text-sm">
                      Step Line
                    </Label>
                    <Switch
                      id="step"
                      checked={(config.step as boolean | undefined) ?? false}
                      onCheckedChange={(c) => updateConfig("step", c)}
                    />
                  </div>
                </>
              )}
              {widgetType === "line_chart" && (
                <div className="flex items-center justify-between">
                  <Label htmlFor="area_fill" className="text-sm">
                    Area Fill
                  </Label>
                  <Switch
                    id="area_fill"
                    checked={(config.area_fill as boolean | undefined) ?? false}
                    onCheckedChange={(c) => updateConfig("area_fill", c)}
                  />
                </div>
              )}
              {widgetType === "area_chart" && (
                <div className="flex items-center justify-between">
                  <Label htmlFor="stacked" className="text-sm">
                    Stacked
                  </Label>
                  <Switch
                    id="stacked"
                    checked={(config.stacked as boolean | undefined) ?? false}
                    onCheckedChange={(c) => updateConfig("stacked", c)}
                  />
                </div>
              )}
              {widgetType === "bar_chart" && (
                <>
                  <div className="flex items-center justify-between">
                    <Label htmlFor="stacked" className="text-sm">
                      Stacked
                    </Label>
                    <Switch
                      id="stacked"
                      checked={(config.stacked as boolean | undefined) ?? false}
                      onCheckedChange={(c) => updateConfig("stacked", c)}
                    />
                  </div>
                  <div className="flex items-center justify-between">
                    <Label htmlFor="horizontal" className="text-sm">
                      Horizontal
                    </Label>
                    <Switch
                      id="horizontal"
                      checked={(config.horizontal as boolean | undefined) ?? false}
                      onCheckedChange={(c) => updateConfig("horizontal", c)}
                    />
                  </div>
                </>
              )}
            </div>
          </div>
        )}
      </>
    );
  }

  function renderThresholdsTab() {
    return (
      <>
        <div className="flex items-center justify-between gap-3">
          <p className="text-sm text-muted-foreground">
            Add color thresholds to highlight when values cross boundaries.
          </p>
          <Button
            variant="outline"
            size="sm"
            onClick={() => {
              const thresholds =
                (config.thresholds as Array<{ value: number; color: string; label?: string }>) ??
                [];
              updateConfig("thresholds", [
                ...thresholds,
                { value: 0, color: "#ef4444", label: "" },
              ]);
            }}
          >
            <Plus className="h-3 w-3 mr-1" /> Add
          </Button>
        </div>

        {(
          (config.thresholds as Array<{ value: number; color: string; label?: string }>) ?? []
        ).map((t, i) => (
          <div key={i} className="flex items-center gap-2">
            <Input
              type="number"
              placeholder="Value"
              value={t.value}
              onChange={(e) => {
                const thresholds = [
                  ...((config.thresholds as Array<{ value: number; color: string; label?: string }>) ??
                    []),
                ];
                thresholds[i] = { ...thresholds[i], value: Number(e.target.value) };
                updateConfig("thresholds", thresholds);
              }}
              className="w-24"
            />
            <input
              type="color"
              value={t.color}
              onChange={(e) => {
                const thresholds = [
                  ...((config.thresholds as Array<{ value: number; color: string; label?: string }>) ??
                    []),
                ];
                thresholds[i] = { ...thresholds[i], color: e.target.value };
                updateConfig("thresholds", thresholds);
              }}
              className="h-8 w-8 cursor-pointer rounded border border-border"
            />
            <Input
              placeholder="Label (optional)"
              value={t.label ?? ""}
              onChange={(e) => {
                const thresholds = [
                  ...((config.thresholds as Array<{ value: number; color: string; label?: string }>) ??
                    []),
                ];
                thresholds[i] = { ...thresholds[i], label: e.target.value };
                updateConfig("thresholds", thresholds);
              }}
              className="flex-1"
            />
            <Button
              variant="ghost"
              size="sm"
              onClick={() => {
                const thresholds = (
                  (config.thresholds as Array<{ value: number; color: string; label?: string }>) ??
                  []
                ).filter((_, j) => j !== i);
                updateConfig("thresholds", thresholds);
              }}
            >
              <X className="h-3 w-3" />
            </Button>
          </div>
        ))}

        {((config.thresholds as unknown[]) ?? []).length === 0 && (
          <p className="text-xs text-muted-foreground">
            No thresholds configured. Add one to color-code values.
          </p>
        )}
      </>
    );
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[600px] max-h-[85vh] flex flex-col">
        <DialogHeader>
          <DialogTitle>Configure {definition?.label || "Widget"}</DialogTitle>
        </DialogHeader>

        <div className="flex-1 overflow-hidden">
          <div className="space-y-2 px-1 pt-4 pb-2">
            <Label>Title</Label>
            <Input
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="Widget title"
              maxLength={100}
            />
          </div>

          {needsTabs ? (
            <Tabs defaultValue="data" className="flex-1">
              <TabsList className="w-full">
                <TabsTrigger value="data">Data</TabsTrigger>
                <TabsTrigger value="style">Style</TabsTrigger>
                {hasThresholds && <TabsTrigger value="thresholds">Thresholds</TabsTrigger>}
              </TabsList>

              <ScrollArea className="h-[50vh] px-1">
                <TabsContent value="data" className="space-y-4 py-3">
                  {renderDataTab()}
                </TabsContent>

                <TabsContent value="style" className="space-y-4 py-3">
                  {renderStyleTab()}
                </TabsContent>

                {hasThresholds && (
                  <TabsContent value="thresholds" className="space-y-3 py-3">
                    {renderThresholdsTab()}
                  </TabsContent>
                )}
              </ScrollArea>
            </Tabs>
          ) : (
            <ScrollArea className="h-[50vh] px-1">
              <div className="space-y-4 py-3">{renderConfigFields()}</div>
            </ScrollArea>
          )}
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

