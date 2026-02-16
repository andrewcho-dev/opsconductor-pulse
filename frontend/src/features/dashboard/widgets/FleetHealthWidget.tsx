import { useQuery } from "@tanstack/react-query";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { fetchFleetHealth } from "@/services/api/devices";

function scoreColor(score: number): string {
  if (score > 80) return "text-green-500";
  if (score >= 50) return "text-yellow-500";
  return "text-red-500";
}

function strokeColor(score: number): string {
  if (score > 80) return "stroke-green-500";
  if (score >= 50) return "stroke-yellow-500";
  return "stroke-red-500";
}

function trackColor(score: number): string {
  if (score > 80) return "stroke-green-500/20";
  if (score >= 50) return "stroke-yellow-500/20";
  return "stroke-red-500/20";
}

export function FleetHealthWidget() {
  const { data, isLoading } = useQuery({
    queryKey: ["fleet-health"],
    queryFn: fetchFleetHealth,
    refetchInterval: 30000,
  });

  const score = data?.score ?? 0;
  const total = data?.total_devices ?? 0;
  const online = data?.online ?? 0;
  const critical = data?.critical_alerts ?? 0;
  const healthy = Math.max(0, online - critical);

  // SVG circular gauge parameters
  const size = 120;
  const strokeWidth = 10;
  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  const progress = (score / 100) * circumference;
  const dashOffset = circumference - progress;

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Fleet Health</CardTitle>
        </CardHeader>
        <CardContent className="flex items-center justify-center py-8">
          <div className="h-[120px] w-[120px] animate-pulse rounded-full bg-muted" />
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Fleet Health</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="flex items-center gap-6">
          <div className="relative flex-shrink-0">
            <svg
              width={size}
              height={size}
              viewBox={`0 0 ${size} ${size}`}
              className="-rotate-90"
            >
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
              <span className={`text-2xl font-bold ${scoreColor(score)}`}>{score}%</span>
            </div>
          </div>

          <div className="space-y-1 text-sm">
            <div>
              <span className="font-medium">{healthy}</span>
              <span className="text-muted-foreground">/{total} devices healthy</span>
            </div>
            <div className="text-xs text-muted-foreground">
              {online} online, {critical} with critical alerts
            </div>
            {score <= 50 && (
              <div className="text-xs font-medium text-red-500">Fleet health is degraded</div>
            )}
            {score > 50 && score <= 80 && (
              <div className="text-xs font-medium text-yellow-500">
                Some devices need attention
              </div>
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
