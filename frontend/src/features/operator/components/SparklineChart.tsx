import { useMemo } from "react";
import { useUIStore } from "@/stores/ui-store";

interface SparklineChartProps {
  data: { time: string; value: number }[];
  height?: number;
  width?: number;
  color?: string;
  showArea?: boolean;
  showLastValue?: boolean;
  unit?: string;
  label?: string;
}

export function SparklineChart({
  data,
  height = 40,
  width = 120,
  color,
  showArea = true,
  showLastValue = true,
  unit = "",
  label,
}: SparklineChartProps) {
  const resolvedTheme = useUIStore((state) => state.resolvedTheme);
  const isDark = resolvedTheme === "dark";

  const chartColor = color || (isDark ? "#60a5fa" : "#3b82f6");
  const areaColor = color || (isDark ? "rgba(96, 165, 250, 0.2)" : "rgba(59, 130, 246, 0.2)");

  const { path, areaPath, minValue, maxValue, lastValue } = useMemo(() => {
    if (!data || data.length === 0) {
      return { path: "", areaPath: "", minValue: 0, maxValue: 0, lastValue: 0 };
    }

    const values = data.map((d) => d.value);
    const min = Math.min(...values);
    const max = Math.max(...values);
    const range = max - min || 1;

    const padding = 2;
    const chartWidth = width - padding * 2;
    const chartHeight = height - padding * 2;

    const points = data.map((d, i) => {
      const x = padding + (i / (data.length - 1)) * chartWidth;
      const y = padding + chartHeight - ((d.value - min) / range) * chartHeight;
      return { x, y };
    });

    const linePath = points
      .map((p, i) => (i === 0 ? `M ${p.x} ${p.y}` : `L ${p.x} ${p.y}`))
      .join(" ");

    const areaPathStr =
      linePath +
      ` L ${points[points.length - 1].x} ${height - padding}` +
      ` L ${padding} ${height - padding} Z`;

    return {
      path: linePath,
      areaPath: areaPathStr,
      minValue: min,
      maxValue: max,
      lastValue: values[values.length - 1],
    };
  }, [data, width, height]);

  if (!data || data.length === 0) {
    return (
      <div
        className="flex items-center justify-center text-muted-foreground text-sm"
        style={{ width, height }}
      >
        No data
      </div>
    );
  }

  return (
    <div className="flex flex-col">
      {label && (
        <span className="text-sm text-muted-foreground mb-1">{label}</span>
      )}
      <div className="flex items-end gap-2">
        <svg width={width} height={height} className="overflow-visible">
          {showArea && <path d={areaPath} fill={areaColor} />}
          <path
            d={path}
            fill="none"
            stroke={chartColor}
            strokeWidth={1.5}
            strokeLinecap="round"
            strokeLinejoin="round"
          />
          {data.length > 0 && (
            <circle
              cx={width - 2}
              cy={
                2 +
                (height - 4) -
                ((lastValue - minValue) / (maxValue - minValue || 1)) *
                  (height - 4)
              }
              r={3}
              fill={chartColor}
            />
          )}
        </svg>
        {showLastValue && (
          <span className="text-lg font-semibold tabular-nums">
            {typeof lastValue === "number"
              ? lastValue.toLocaleString(undefined, { maximumFractionDigits: 1 })
              : lastValue}
            {unit && <span className="text-sm text-muted-foreground ml-0.5">{unit}</span>}
          </span>
        )}
      </div>
    </div>
  );
}
