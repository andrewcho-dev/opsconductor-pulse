import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { Card, CardContent } from "@/components/ui/card";
import { SparklineChart } from "./SparklineChart";
import { fetchMetricHistory } from "@/services/api/system";
import { TrendingUp, TrendingDown, Minus } from "lucide-react";

interface MetricChartCardProps {
  title: string;
  metric: string;
  unit?: string;
  icon?: React.ElementType;
  color?: string;
  minutes?: number;
  refreshInterval?: number;
}

export function MetricChartCard({
  title,
  metric,
  unit = "",
  icon: Icon,
  color,
  minutes = 15,
  refreshInterval = 10000,
}: MetricChartCardProps) {
  const { data, isLoading } = useQuery({
    queryKey: ["metric-history", metric, minutes],
    queryFn: () => fetchMetricHistory(metric, minutes),
    refetchInterval: refreshInterval,
  });

  const trend = useMemo(() => {
    if (!data?.points || data.points.length < 2) return null;

    const recent = data.points.slice(-6);
    const older = data.points.slice(-12, -6);

    if (recent.length === 0 || older.length === 0) return null;

    const recentAvg = recent.reduce((a, b) => a + b.value, 0) / recent.length;
    const olderAvg = older.reduce((a, b) => a + b.value, 0) / older.length;

    const change = ((recentAvg - olderAvg) / (olderAvg || 1)) * 100;
    const changeAbs = Math.abs(change);

    if (changeAbs < 5) return { direction: "flat", change: 0 };
    return {
      direction: change > 0 ? "up" : "down",
      change: Math.round(changeAbs),
    };
  }, [data?.points]);

  return (
    <Card>
      <CardContent className="p-4">
        <div className="flex items-start justify-between mb-2">
          <div className="flex items-center gap-2 text-muted-foreground">
            {Icon && <Icon className="h-4 w-4" />}
            <span className="text-sm font-medium">{title}</span>
          </div>
          {trend && (
            <div
              className={`flex items-center gap-1 text-xs ${
                trend.direction === "up"
                  ? "text-green-600 dark:text-green-400"
                  : trend.direction === "down"
                  ? "text-red-600 dark:text-red-400"
                  : "text-muted-foreground"
              }`}
            >
              {trend.direction === "up" && <TrendingUp className="h-3 w-3" />}
              {trend.direction === "down" && <TrendingDown className="h-3 w-3" />}
              {trend.direction === "flat" && <Minus className="h-3 w-3" />}
              {trend.change > 0 && <span>{trend.change}%</span>}
            </div>
          )}
        </div>

        {isLoading ? (
          <div className="h-10 flex items-center justify-center text-muted-foreground text-sm">
            Loading...
          </div>
        ) : (
          <SparklineChart
            data={data?.points || []}
            width={200}
            height={50}
            color={color}
            unit={unit}
          />
        )}

        <div className="text-xs text-muted-foreground mt-2">
          Last {minutes} minutes
        </div>
      </CardContent>
    </Card>
  );
}
