import { useMemo, memo } from "react";
import { EChartWrapper } from "./EChartWrapper";
import { getMetricConfig } from "./metric-config";
import type { EChartsOption } from "echarts";

interface MetricGaugeProps {
  metricName: string;
  value: number | null;
  /** Optional data values for auto-scaling unknown metrics */
  allValues?: number[];
  className?: string;
}

function MetricGaugeInner({
  metricName,
  value,
  allValues,
  className,
}: MetricGaugeProps) {
  const config = useMemo(
    () => getMetricConfig(metricName, allValues),
    [metricName, allValues]
  );

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
            lineStyle: { width: 1, color: "#52525b" },
          },
          axisLabel: {
            distance: 16,
            fontSize: 10,
            color: "#71717a",
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
              borderColor: "#52525b",
            },
          },
          title: {
            offsetCenter: [0, "70%"],
            fontSize: 12,
            color: "#a1a1aa",
          },
          detail: {
            valueAnimation: true,
            offsetCenter: [0, "45%"],
            fontSize: 20,
            fontWeight: "bold",
            color: "#fafafa",
            formatter: (v: number) => {
              if (v == null) return "—";
              return `${v.toFixed(config.precision)}${config.unit}`;
            },
          },
          data: [
            {
              value: value ?? 0,
              name: config.label,
            },
          ],
        },
      ],
    };
  }, [value, config]);

  return (
    <EChartWrapper
      option={option}
      className={className}
      style={{ height: 180 }}
    />
  );
}

export const MetricGauge = memo(MetricGaugeInner);
