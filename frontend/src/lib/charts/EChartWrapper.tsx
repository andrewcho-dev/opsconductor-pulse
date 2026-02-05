import { useEffect, useRef } from "react";
import * as echarts from "echarts";
import { ECHARTS_THEME } from "./theme";
import { cn } from "@/lib/utils";

interface EChartWrapperProps {
  option: echarts.EChartsOption;
  className?: string;
  style?: React.CSSProperties;
  /** If true, merge new options instead of replacing */
  notMerge?: boolean;
}

export function EChartWrapper({
  option,
  className,
  style,
  notMerge = false,
}: EChartWrapperProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<echarts.ECharts | null>(null);

  // Initialize chart
  useEffect(() => {
    if (!containerRef.current) return;

    const chart = echarts.init(containerRef.current, ECHARTS_THEME, {
      renderer: "canvas",
    });
    chartRef.current = chart;

    // ResizeObserver for responsive sizing
    const observer = new ResizeObserver(() => {
      chart.resize();
    });
    observer.observe(containerRef.current);

    return () => {
      observer.disconnect();
      chart.dispose();
      chartRef.current = null;
    };
  }, []);

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
