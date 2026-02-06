import { useMemo, memo } from "react";
import type uPlot from "uplot";
import { UPlotChart } from "./UPlotChart";
import { toUPlotData } from "./transforms";
import { getMetricConfig } from "./metric-config";
import { getSeriesColor } from "./colors";
import type { TelemetryPoint } from "@/services/api/types";
import { useUIStore } from "@/stores/ui-store";

interface TimeSeriesChartProps {
  metricName: string;
  points: TelemetryPoint[];
  colorIndex?: number;
  height?: number;
  className?: string;
}

function TimeSeriesChartInner({
  metricName,
  points,
  colorIndex = 0,
  height = 200,
  className,
}: TimeSeriesChartProps) {
  const resolvedTheme = useUIStore((s) => s.resolvedTheme);
  const axisColor = resolvedTheme === "dark" ? "#71717a" : "#52525b";
  const gridColor = resolvedTheme === "dark" ? "#27272a" : "#e4e4e7";
  const tickColor = resolvedTheme === "dark" ? "#3f3f46" : "#d4d4d8";
  const config = useMemo(
    () => getMetricConfig(metricName),
    [metricName]
  );

  const data = useMemo(
    () => toUPlotData(points, metricName) as uPlot.AlignedData,
    [points, metricName]
  );

  const options = useMemo<Omit<uPlot.Options, "width" | "height">>(
    () => ({
      scales: {
        x: { time: true },
        y: {},
      },
      axes: [
        {
          // X-axis (time)
          stroke: axisColor,
          grid: { stroke: gridColor, width: 1 },
          ticks: { stroke: tickColor, width: 1 },
        },
        {
          // Y-axis (values)
          stroke: axisColor,
          grid: { stroke: gridColor, width: 1 },
          ticks: { stroke: tickColor, width: 1 },
          label: `${config.label}${config.unit ? ` (${config.unit})` : ""}`,
          labelSize: 16,
          labelFont: "11px system-ui",
          size: 60,
        },
      ],
      cursor: {
        drag: { x: false, y: false },
      },
      series: [
        {}, // timestamps series (always first, no config)
        {
          label: config.label,
          stroke: getSeriesColor(colorIndex),
          width: 2,
          points: { show: false },
          spanGaps: true,
        },
      ],
    }),
    [config, colorIndex, axisColor, gridColor, tickColor]
  );

  if (data[0].length === 0) {
    return (
      <div
        className="flex items-center justify-center text-sm text-muted-foreground border border-border rounded-md"
        style={{ height }}
      >
        No data for {config.label}
      </div>
    );
  }

  return (
    <UPlotChart
      options={options}
      data={data}
      height={height}
      className={className}
    />
  );
}

export const TimeSeriesChart = memo(TimeSeriesChartInner);
