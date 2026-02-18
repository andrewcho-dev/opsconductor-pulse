import { useQuery } from "@tanstack/react-query";
import { fetchFleetHealth } from "@/services/api/devices";
import { Skeleton } from "@/components/ui/skeleton";
import type { WidgetRendererProps } from "../widget-registry";

function scoreColor(score: number): string {
  if (score > 80) return "text-status-online";
  if (score >= 50) return "text-status-warning";
  return "text-status-critical";
}

function strokeColor(score: number): string {
  if (score > 80) return "stroke-status-online";
  if (score >= 50) return "stroke-status-warning";
  return "stroke-status-critical";
}

function trackColor(score: number): string {
  if (score > 80) return "stroke-status-online/20";
  if (score >= 50) return "stroke-status-warning/20";
  return "stroke-status-critical/20";
}

export default function HealthScoreRenderer({ config }: WidgetRendererProps) {
  const { data, isLoading } = useQuery({
    queryKey: ["widget-fleet-health"],
    queryFn: fetchFleetHealth,
    refetchInterval: 30000,
  });

  const decimalPrecision = (config.decimal_precision as number | undefined) ?? 1;
  const score = data?.score ?? 0;
  const total = data?.total_devices ?? 0;
  const online = data?.online ?? 0;
  const critical = data?.critical_alerts ?? 0;
  const healthy = Math.max(0, online - critical);

  const size = 120;
  const strokeWidth = 10;
  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  const progress = (score / 100) * circumference;
  const dashOffset = circumference - progress;

  if (isLoading) return <Skeleton className="h-[140px] w-full" />;

  return (
    <div className="h-full flex items-center gap-4 px-2">
      <div className="relative shrink-0">
        <svg viewBox="0 0 120 120" className="h-full max-h-[120px] w-auto shrink-0 -rotate-90">
          <circle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            fill="none"
            strokeWidth={strokeWidth}
            className={trackColor(score)}
          />
          <circle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            fill="none"
            strokeWidth={strokeWidth}
            strokeLinecap="round"
            strokeDasharray={circumference}
            strokeDashoffset={dashOffset}
            className={`${strokeColor(score)} transition-all duration-700`}
          />
        </svg>
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className={`text-2xl font-semibold ${scoreColor(score)}`}>
            {score.toFixed(decimalPrecision)}%
          </span>
        </div>
      </div>

      <div className="flex flex-col gap-1 min-w-0 text-sm">
        <div>
          <span className="font-medium">{healthy}</span>
          <span className="text-muted-foreground">/{total} devices healthy</span>
        </div>
        <div className="text-xs text-muted-foreground">
          {online} online, {critical} with critical alerts
        </div>
      </div>
    </div>
  );
}

