import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { SparklineChart } from "./SparklineChart";
import { fetchMetricHistory } from "@/services/api/system";
import { TrendingUp, TrendingDown } from "lucide-react";

interface MetricChartCardProps {
  title: string;
  metric: string;
  unit?: string;
  icon?: React.ElementType;
  color?: string;
  minutes?: number;
  refreshInterval?: number;
  rate?: boolean;
}

export function MetricChartCard({
  title,
  metric,
  unit = "",
  icon: Icon,
  color = "#3b82f6",
  minutes = 15,
  refreshInterval = 10000,
  rate = false,
}: MetricChartCardProps) {
  const { data, isLoading } = useQuery({
    queryKey: ["metric-history", metric, minutes, rate],
    queryFn: () => fetchMetricHistory(metric, minutes, rate),
    refetchInterval: refreshInterval,
  });

  const { currentValue, trend } = useMemo(() => {
    if (!data?.points || data.points.length < 2) {
      return { currentValue: null, trend: null };
    }

    const current = data.points[data.points.length - 1]?.value ?? null;
    const recent = data.points.slice(-6);
    const older = data.points.slice(-12, -6);

    if (recent.length === 0 || older.length === 0) {
      return { currentValue: current, trend: null };
    }

    const recentAvg = recent.reduce((a, b) => a + b.value, 0) / recent.length;
    const olderAvg = older.reduce((a, b) => a + b.value, 0) / older.length;
    const change = ((recentAvg - olderAvg) / (olderAvg || 1)) * 100;

    return {
      currentValue: current,
      trend: Math.abs(change) < 5 ? null : { up: change > 0, pct: Math.round(Math.abs(change)) },
    };
  }, [data?.points]);

  const formatValue = (v: number | null) => {
    if (v === null) return "—";
    if (v >= 1000000) return `${(v / 1000000).toFixed(1)}M`;
    if (v >= 1000) return `${(v / 1000).toFixed(1)}K`;
    return v.toFixed(v % 1 === 0 ? 0 : 1);
  };

  return (
    <div className="flex items-center gap-2 px-2 py-1 rounded border border-border bg-card min-w-0">
      {Icon && <Icon className="h-3 w-3 text-muted-foreground shrink-0" />}
      <span className="text-[11px] text-muted-foreground truncate">{title}</span>
      <span className="text-xs font-semibold tabular-nums" style={{ color }}>
        {formatValue(currentValue)}{unit}
      </span>
      {trend && (
        <span className={`flex items-center text-[10px] ${trend.up ? "text-green-600" : "text-red-600"}`}>
          {trend.up ? <TrendingUp className="h-2.5 w-2.5" /> : <TrendingDown className="h-2.5 w-2.5" />}
          {trend.pct}%
        </span>
      )}
      <div className="flex-1 min-w-12 max-w-24">
        {isLoading ? (
          <div className="h-6 bg-muted/50 rounded animate-pulse" />
        ) : (
          <SparklineChart data={data?.points || []} width={96} height={24} color={color} unit={unit} />
        )}
      </div>
    </div>
  );
}
