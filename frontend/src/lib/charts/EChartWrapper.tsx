import { useEffect, useRef, memo } from "react";
import * as echarts from "echarts";
import { ECHARTS_DARK_THEME, ECHARTS_LIGHT_THEME } from "./theme";
import { cn } from "@/lib/utils";
import { useUIStore } from "@/stores/ui-store";
import type { ECharts } from "echarts";

interface EChartWrapperProps {
  option: echarts.EChartsOption;
  className?: string;
  style?: React.CSSProperties;
  /** If true, merge new options instead of replacing */
  notMerge?: boolean;
}

function EChartWrapperInner({
  option,
  className,
  style,
  notMerge = false,
}: EChartWrapperProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<ECharts | null>(null);
  const resolvedTheme = useUIStore((s) => s.resolvedTheme);
  const echartsTheme = resolvedTheme === "dark" ? ECHARTS_DARK_THEME : ECHARTS_LIGHT_THEME;

  // Initialize chart
  useEffect(() => {
    if (!containerRef.current) return;

    if (chartRef.current) {
      chartRef.current.dispose();
    }

    const chart = echarts.init(containerRef.current, echartsTheme, {
      renderer: "canvas",
    });
    chartRef.current = chart;
    chartRef.current.setOption(option);

    // ResizeObserver for responsive sizing
    const observer = new ResizeObserver(() => {
      chart.resize();
    });
    observer.observe(containerRef.current);

    return () => {
      observer.disconnect();
      chartRef.current?.dispose();
      chartRef.current = null;
    };
  }, [echartsTheme]);

  // Update options when they change
  useEffect(() => {
    if (chartRef.current) {
      chartRef.current.setOption(option, notMerge);
    }
  }, [option, notMerge]);

  return (
    <div
      ref={containerRef}
      className={cn("w-full", className)}
      style={{ height: 200, ...style }}
    />
  );
}

export const EChartWrapper = memo(EChartWrapperInner);
