import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { fetchTenantStats } from "@/services/api/tenants";

interface TenantActivitySparklineProps {
  tenantId: string;
  height?: number;
  width?: number;
}

export default function TenantActivitySparkline({
  tenantId,
  height = 24,
  width = 80,
}: TenantActivitySparklineProps) {
  const { data } = useQuery({
    queryKey: ["tenant-activity-sparkline", tenantId],
    queryFn: () => fetchTenantStats(tenantId),
    refetchInterval: 60000,
  });

  const values = useMemo(() => {
    const online = data?.stats.devices.online ?? 0;
    const stale = data?.stats.devices.stale ?? 0;
    const alerts = data?.stats.alerts.open ?? 0;
    // Stats endpoint currently returns snapshots, so we synthesize a small series.
    return [Math.max(0, online - stale), online, online + Math.min(alerts, 8), online];
  }, [data]);

  const min = Math.min(...values, 0);
  const max = Math.max(...values, 1);
  const range = Math.max(max - min, 1);
  const points = values
    .map((value, i) => {
      const x = (i / Math.max(values.length - 1, 1)) * width;
      const y = height - 2 - ((value - min) / range) * (height - 4);
      return `${x},${y}`;
    })
    .join(" ");
  const areaPoints = `0,${height} ${points} ${width},${height}`;

  return (
    <svg
      viewBox={`0 0 ${width} ${height}`}
      preserveAspectRatio="none"
      className="block"
      style={{ width, height }}
    >
      <polygon points={areaPoints} fill="#3b82f6" opacity={0.15} />
      <polyline
        points={points}
        fill="none"
        stroke="#60a5fa"
        strokeWidth={1.5}
        vectorEffect="non-scaling-stroke"
      />
    </svg>
  );
}
