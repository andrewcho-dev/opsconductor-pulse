import { useEffect, useMemo, useState } from "react";
import * as echarts from "echarts";
import { PageHeader } from "@/components/shared";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { EChartWrapper } from "@/lib/charts/EChartWrapper";
import { apiGet } from "@/services/api/client";
import {
  fetchSystemMetricsHistory,
  fetchSystemMetricsLatest,
  type MetricsHistoryPoint,
  type SystemMetricsSnapshot,
} from "@/services/api/operator";

type Aggregates = {
  devices?: { online?: number; stale?: number; offline?: number; total?: number };
  alerts?: { open?: number };
};

function numberOrZero(value: unknown): number {
  return typeof value === "number" && Number.isFinite(value) ? value : 0;
}

function getServiceMetric(snapshot: SystemMetricsSnapshot | null, service: string, metric: string): number {
  if (!snapshot) return 0;
  const serviceObj = snapshot[service] as Record<string, unknown> | undefined;
  return numberOrZero(serviceObj?.[metric]);
}

export default function SystemMetricsPage() {
  const [latest, setLatest] = useState<SystemMetricsSnapshot | null>(null);
  const [history, setHistory] = useState<MetricsHistoryPoint[]>([]);
  const [aggregates, setAggregates] = useState<Aggregates>({});
  const [lastUpdated, setLastUpdated] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string>("");

  async function fetchData() {
    try {
      setError("");
      const [latestResp, historyResp, aggregatesResp] = await Promise.all([
        fetchSystemMetricsLatest(),
        fetchSystemMetricsHistory({ metric: "messages_written", minutes: 60, service: "ingest", rate: true }),
        apiGet<Aggregates>("/operator/system/aggregates"),
      ]);
      setLatest(latestResp);
      setHistory(historyResp.points ?? []);
      setAggregates(aggregatesResp);
      setLastUpdated(new Date().toISOString());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load metrics");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 30_000);
    return () => clearInterval(interval);
  }, []);

  const ingestOption = useMemo<echarts.EChartsOption>(
    () => ({
      tooltip: { trigger: "axis" },
      xAxis: { type: "time" },
      yAxis: { type: "value", name: "msg/s" },
      series: [
        {
          type: "line",
          smooth: true,
          step: "end",
          data: history.map((point) => [point.time, point.value]),
        },
      ],
    }),
    [history]
  );

  const activeAlertsOption = useMemo<echarts.EChartsOption>(() => {
    const allTenantsLabel = ["all-tenants"];
    const openAlerts = numberOrZero(aggregates.alerts?.open);
    return {
      tooltip: { trigger: "axis" },
      xAxis: { type: "category", data: allTenantsLabel },
      yAxis: { type: "value" },
      series: [
        {
          type: "bar",
          data: [
            {
              value: openAlerts,
              itemStyle: { color: openAlerts > 0 ? "#ef4444" : "#22c55e" },
            },
          ],
        },
      ],
    };
  }, [aggregates.alerts?.open]);

  const deviceStatusOption = useMemo<echarts.EChartsOption>(() => {
    const online = numberOrZero(aggregates.devices?.online);
    const stale = numberOrZero(aggregates.devices?.stale);
    const offline = numberOrZero(aggregates.devices?.offline);
    return {
      tooltip: { trigger: "item" },
      series: [
        {
          type: "pie",
          radius: "70%",
          data: [
            { value: online, name: "ONLINE", itemStyle: { color: "#22c55e" } },
            { value: stale, name: "STALE", itemStyle: { color: "#f59e0b" } },
            { value: offline, name: "OFFLINE", itemStyle: { color: "#ef4444" } },
          ],
        },
      ],
    };
  }, [aggregates.devices?.offline, aggregates.devices?.online, aggregates.devices?.stale]);

  const deliveryFailures = getServiceMetric(latest, "delivery", "jobs_failed");

  return (
    <div className="space-y-4">
      <PageHeader
        title="System Metrics"
        description={
          lastUpdated
            ? `Last updated: ${new Date(lastUpdated).toLocaleString()}`
            : "Loading latest metrics..."
        }
        action={<Badge variant="outline">Auto-refreshing every 30s</Badge>}
      />

      {error && <div className="text-sm text-destructive">{error}</div>}

      <div className="grid gap-3 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Ingest Rate</CardTitle>
          </CardHeader>
          <CardContent>
            <EChartWrapper option={ingestOption} style={{ height: 280 }} />
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Active Alerts by Tenant</CardTitle>
          </CardHeader>
          <CardContent>
            <EChartWrapper option={activeAlertsOption} style={{ height: 280 }} />
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Device Status Breakdown</CardTitle>
          </CardHeader>
          <CardContent>
            <EChartWrapper option={deviceStatusOption} style={{ height: 280 }} />
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Delivery Failures</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-1">
              <div className="text-2xl font-semibold">{deliveryFailures}</div>
              <p className="text-xs text-muted-foreground">Since service start</p>
              {loading && <p className="text-xs text-muted-foreground">Loading...</p>}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
