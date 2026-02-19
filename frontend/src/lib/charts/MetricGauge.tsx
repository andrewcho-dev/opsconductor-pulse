import { useMemo, memo } from "react";
import { EChartWrapper } from "./EChartWrapper";
import { getMetricConfig } from "./metric-config";
import type { EChartsOption } from "echarts";
import { useUIStore } from "@/stores/ui-store";

interface MetricGaugeProps {
  metricName: string;
  value: number | null;
  /** Optional overrides for per-device sensor labeling */
  displayLabel?: string;
  unit?: string;
  /** Optional data values for auto-scaling unknown metrics */
  allValues?: number[];
  className?: string;
}

function MetricGaugeInner({
  metricName,
  value,
  displayLabel,
  unit,
  allValues,
  className,
}: MetricGaugeProps) {
  const resolvedTheme = useUIStore((s) => s.resolvedTheme);
  const textColor = resolvedTheme === "dark" ? "#fafafa" : "#18181b";
  const mutedColor = resolvedTheme === "dark" ? "#a1a1aa" : "#71717a";
  const axisLabelColor = resolvedTheme === "dark" ? "#71717a" : "#52525b";
  const lineColor = resolvedTheme === "dark" ? "#52525b" : "#d4d4d8";
  const config = useMemo(
    () => getMetricConfig(metricName, allValues),
    [metricName, allValues]
  );
  const effectiveLabel = displayLabel?.trim() ? displayLabel.trim() : config.label;
  const effectiveUnit = unit?.trim()
    ? ` ${unit.trim()}`
    : config.unit?.trim()
      ? config.unit.trim()
      : "";

  const option = useMemo<EChartsOption>(() => {
    // Build color stops for the gauge arc from zones
    const axisLineColors: [number, string][] = config.zones.map((z) => {
      const stop = (z.max - config.min) / (config.max - config.min);
      return [Math.min(1, Math.max(0, stop)), z.color];
    });

    return {
      series: [
        {
          type: "gauge",
          startAngle: 210,
          endAngle: -30,
          min: config.min,
          max: config.max,
          radius: "90%",
          progress: {
            show: true,
            width: 12,
          },
          axisLine: {
            lineStyle: {
              width: 12,
              color: axisLineColors,
            },
          },
          axisTick: { show: false },
          splitLine: {
            length: 8,
            lineStyle: { width: 1, color: lineColor },
          },
          axisLabel: {
            distance: 16,
            fontSize: 10,
            color: axisLabelColor,
            formatter: (v: number) => {
              if (v === config.min || v === config.max) {
                return `${v}`;
              }
              return "";
            },
          },
          pointer: {
            length: "55%",
            width: 4,
            itemStyle: { color: "auto" },
          },
          anchor: {
            show: true,
            size: 8,
            itemStyle: {
              borderWidth: 2,
              borderColor: lineColor,
            },
          },
          title: {
            offsetCenter: [0, "70%"],
            fontSize: 12,
            color: mutedColor,
          },
          detail: {
            valueAnimation: true,
            offsetCenter: [0, "45%"],
            fontSize: 20,
            fontWeight: "bold",
            color: textColor,
            formatter: (v: number) => {
              if (v == null) return "—";
              return `${v.toFixed(config.precision)}${effectiveUnit}`;
            },
          },
          data: [
            {
              value: value ?? 0,
              name: effectiveLabel,
            },
          ],
        },
      ],
    };
  }, [
    value,
    config,
    effectiveLabel,
    effectiveUnit,
    textColor,
    mutedColor,
    axisLabelColor,
    lineColor,
  ]);

  return (
    <EChartWrapper
      option={option}
      className={className}
      style={{ height: 180 }}
    />
  );
}

export const MetricGauge = memo(MetricGaugeInner);
