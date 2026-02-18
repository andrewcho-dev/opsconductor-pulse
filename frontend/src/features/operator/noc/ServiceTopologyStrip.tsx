import { useQuery } from "@tanstack/react-query";
import {
  AlertTriangle,
  Database,
  Radio,
  Send,
  Shield,
  Truck,
  Upload,
  type LucideIcon,
} from "lucide-react";
import { fetchSystemHealth, type ComponentHealth } from "@/services/api/system";
import { NOC_COLORS } from "./nocColors";

interface ServiceTopologyStripProps {
  refreshInterval: number;
  isPaused: boolean;
}

interface ServiceNode {
  key: string;
  label: string;
  icon: LucideIcon;
}

const PIPELINE: ServiceNode[] = [
  { key: "mqtt", label: "MQTT", icon: Radio },
  { key: "ingest", label: "Ingest", icon: Upload },
  { key: "postgres", label: "TimescaleDB", icon: Database },
  { key: "evaluator", label: "Evaluator", icon: AlertTriangle },
  { key: "dispatcher", label: "Dispatcher", icon: Send },
  { key: "delivery", label: "Delivery", icon: Truck },
];

const SUPPORT_SERVICES: ServiceNode[] = [{ key: "keycloak", label: "Keycloak", icon: Shield }];

function nodeStyle(status: string) {
  const base = "flex min-w-20 flex-col items-center gap-1 rounded-lg border px-3 py-2 text-sm";
  if (status === "healthy") return `${base} border-green-500/50 bg-green-500/5 text-green-400`;
  if (status === "degraded") return `${base} border-yellow-500/50 bg-yellow-500/5 text-yellow-400`;
  if (status === "down") return `${base} border-red-500/50 bg-red-500/5 text-red-400`;
  return `${base} border-gray-600 bg-gray-800/50 text-gray-400`;
}

function ServiceNodeCard({ node, health }: { node: ServiceNode; health?: ComponentHealth }) {
  const status = health?.status ?? "unknown";
  const Icon = node.icon;
  return (
    <div className={nodeStyle(status)}>
      <div className="flex items-center gap-1">
        <span
          className="inline-block h-2 w-2 rounded-full"
          style={{
            backgroundColor:
              status === "healthy"
                ? NOC_COLORS.healthy
                : status === "degraded"
                  ? NOC_COLORS.warning
                  : status === "down"
                    ? NOC_COLORS.critical
                    : NOC_COLORS.neutral,
          }}
        />
        <Icon className="h-3.5 w-3.5" />
      </div>
      <div className="font-medium">{node.label}</div>
      <div className="text-xs opacity-80">
        {typeof health?.latency_ms === "number" ? `${health.latency_ms}ms` : "n/a"}
      </div>
    </div>
  );
}

export function ServiceTopologyStrip({ refreshInterval, isPaused }: ServiceTopologyStripProps) {
  const { data: health } = useQuery({
    queryKey: ["noc-service-health"],
    queryFn: fetchSystemHealth,
    refetchInterval: isPaused ? false : refreshInterval,
  });

  return (
    <div
      className="space-y-3 rounded-lg border p-4"
      style={{ borderColor: NOC_COLORS.bg.cardBorder, backgroundColor: NOC_COLORS.bg.card }}
    >
      <div className="flex items-center justify-between">
        <div className="text-sm font-medium text-gray-200">Service Topology</div>
        <div className="text-sm text-gray-500">
          Last checked:{" "}
          {health?.checked_at ? new Date(health.checked_at).toLocaleTimeString() : "—"}
        </div>
      </div>

      <div className="flex flex-wrap items-center gap-1">
        {PIPELINE.map((node, idx) => (
          <div key={node.key} className="flex items-center gap-1">
            <ServiceNodeCard
              node={node}
              health={health?.components?.[node.key as keyof typeof health.components]}
            />
            {idx < PIPELINE.length - 1 && (
              <div className="flex items-center text-sm text-gray-600">──►</div>
            )}
          </div>
        ))}
      </div>

      <div className="flex flex-wrap items-center gap-2">
        <span className="text-sm text-gray-500">Support:</span>
        {SUPPORT_SERVICES.map((node) => (
          <ServiceNodeCard
            key={node.key}
            node={node}
            health={health?.components?.[node.key as keyof typeof health.components]}
          />
        ))}
      </div>
    </div>
  );
}
