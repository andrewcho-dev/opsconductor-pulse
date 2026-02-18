import { useMemo, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { toast } from "sonner";
import {
  fetchAvailableMetrics,
  runAnalyticsQuery,
  downloadAnalyticsCSV,
} from "@/services/api/analytics";
import type {
  Aggregation,
  TimeRange,
  GroupBy,
  AnalyticsQueryRequest,
  AnalyticsQueryResponse,
} from "@/services/api/analytics";
import { fetchDevices, fetchDeviceGroups } from "@/services/api/devices";
import { EChartWrapper } from "@/lib/charts/EChartWrapper";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { DataTable } from "@/components/ui/data-table";
import { type ColumnDef } from "@tanstack/react-table";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { BarChart3, Download, Play, Loader2 } from "lucide-react";
import { getErrorMessage } from "@/lib/errors";

const AGGREGATION_OPTIONS: { value: Aggregation; label: string }[] = [
  { value: "avg", label: "Average" },
  { value: "min", label: "Minimum" },
  { value: "max", label: "Maximum" },
  { value: "p95", label: "95th Percentile" },
  { value: "sum", label: "Sum" },
  { value: "count", label: "Count" },
];

const TIME_RANGE_OPTIONS: { value: TimeRange; label: string }[] = [
  { value: "1h", label: "Last 1 hour" },
  { value: "6h", label: "Last 6 hours" },
  { value: "24h", label: "Last 24 hours" },
  { value: "7d", label: "Last 7 days" },
  { value: "30d", label: "Last 30 days" },
];

const GROUP_BY_OPTIONS: { value: string; label: string }[] = [
  { value: "none", label: "No grouping" },
  { value: "device", label: "By Device" },
  { value: "site", label: "By Site" },
  { value: "group", label: "By Device Group" },
];

export default function AnalyticsPage() {
  const [metric, setMetric] = useState<string>("");
  const [aggregation, setAggregation] = useState<Aggregation>("avg");
  const [timeRange, setTimeRange] = useState<TimeRange>("24h");
  const [groupBy, setGroupBy] = useState<string>("none");
  const [selectedDeviceIds, setSelectedDeviceIds] = useState<string[]>([]);
  const [selectedGroupId, setSelectedGroupId] = useState<string>("");

  const [results, setResults] = useState<AnalyticsQueryResponse | null>(null);

  const { data: metricsData, isLoading: metricsLoading } = useQuery({
    queryKey: ["analytics-metrics"],
    queryFn: fetchAvailableMetrics,
  });

  const { data: devicesData } = useQuery({
    queryKey: ["analytics-devices"],
    queryFn: () => fetchDevices({ limit: 500, offset: 0 }),
  });

  const { data: groupsData } = useQuery({
    queryKey: ["analytics-groups"],
    queryFn: fetchDeviceGroups,
  });

  const queryMutation = useMutation({
    mutationFn: runAnalyticsQuery,
    onSuccess: (data) => {
      setResults(data);
      toast.success("Query completed");
    },
    onError: (err: Error) => {
      toast.error(getErrorMessage(err) || "Failed to run query");
    },
  });

  const handleRunQuery = () => {
    if (!metric) return;
    const request: AnalyticsQueryRequest = {
      metric,
      aggregation,
      time_range: timeRange,
      group_by: groupBy === "none" ? null : (groupBy as GroupBy),
      device_ids: selectedDeviceIds.length > 0 ? selectedDeviceIds : undefined,
      group_id: groupBy === "group" && selectedGroupId ? selectedGroupId : undefined,
    };
    queryMutation.mutate(request);
  };

  const handleExport = async () => {
    if (!metric) return;
    const request: AnalyticsQueryRequest = {
      metric,
      aggregation,
      time_range: timeRange,
      group_by: groupBy === "none" ? null : (groupBy as GroupBy),
      device_ids: selectedDeviceIds.length > 0 ? selectedDeviceIds : undefined,
      group_id: groupBy === "group" && selectedGroupId ? selectedGroupId : undefined,
    };
    await downloadAnalyticsCSV(request);
  };

  const chartOption = useMemo(() => {
    if (!results || results.series.length === 0) return null;

    const series = results.series.map((s) => ({
      name: s.label,
      type: "line" as const,
      smooth: true,
      symbol: "circle",
      symbolSize: 4,
      data: s.points.map((p) => [p.time, p.value]),
    }));

    return {
      tooltip: {
        trigger: "axis" as const,
        axisPointer: { type: "cross" as const },
      },
      legend: {
        show: results.series.length > 1 && results.series.length <= 10,
        bottom: 0,
        type: "scroll" as const,
      },
      grid: {
        left: 60,
        right: 20,
        top: 20,
        bottom: results.series.length > 1 ? 40 : 20,
      },
      xAxis: { type: "time" as const },
      yAxis: { type: "value" as const, name: `${aggregation}(${metric})` },
      series,
    };
  }, [results, aggregation, metric]);

  const metrics = metricsData?.metrics ?? [];
  const devices = devicesData?.devices ?? [];
  const groups = groupsData?.groups ?? [];

  const queryResult = useMemo(() => {
    if (!results) return null;
    const rows: Array<Record<string, string>> = [];
    const includeLabel = results.series.length > 1;
    for (const s of results.series) {
      for (const p of s.points) {
        const row: Record<string, string> = {};
        if (includeLabel) row.label = s.label;
        row.time = new Date(p.time).toLocaleString();
        row.value = p.value != null ? p.value.toFixed(2) : "--";
        rows.push(row);
      }
    }
    const columns = rows.length > 0 ? Object.keys(rows[0]) : includeLabel ? ["label", "time", "value"] : ["time", "value"];
    return { columns, rows };
  }, [results]);

  const rawTableColumns: ColumnDef<Record<string, string>>[] = useMemo(() => {
    if (!queryResult?.columns) return [];
    return queryResult.columns.map((col: string) => ({
      accessorKey: col,
      header: col.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase()),
      enableSorting: true,
      cell: ({ row }) => {
        const val = row.original[col] ?? "";
        const mono = col === "time" || col === "value";
        return <span className={mono ? "font-mono text-sm" : ""}>{val}</span>;
      },
    }));
  }, [queryResult?.columns]);

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <BarChart3 className="h-5 w-5" />
          <h1 className="text-lg font-semibold">Analytics</h1>
        </div>
        <Button
          variant="outline"
          size="sm"
          onClick={() => void handleExport()}
          disabled={!metric}
        >
          <Download className="h-4 w-4 mr-2" />
          Export CSV
        </Button>
      </div>

      <div className="flex gap-6">
        {/* Query builder */}
        <div className="w-80 shrink-0 space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="text-sm">Query Builder</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <div className="text-sm font-medium">Metric</div>
                <Select value={metric} onValueChange={setMetric}>
                  <SelectTrigger>
                    <SelectValue
                      placeholder={metricsLoading ? "Loading metrics..." : "Select metric"}
                    />
                  </SelectTrigger>
                  <SelectContent>
                    {metrics.map((m) => (
                      <SelectItem key={m} value={m}>
                        {m}
                      </SelectItem>
                    ))}
                    {metrics.length === 0 && !metricsLoading && (
                      <SelectItem value="__none__" disabled>
                        No metrics found
                      </SelectItem>
                    )}
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-2">
                <div className="text-sm font-medium">Aggregation</div>
                <Select value={aggregation} onValueChange={(v) => setAggregation(v as Aggregation)}>
                  <SelectTrigger>
                    <SelectValue placeholder="Select aggregation" />
                  </SelectTrigger>
                  <SelectContent>
                    {AGGREGATION_OPTIONS.map((opt) => (
                      <SelectItem key={opt.value} value={opt.value}>
                        {opt.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-2">
                <div className="text-sm font-medium">Time Range</div>
                <Select value={timeRange} onValueChange={(v) => setTimeRange(v as TimeRange)}>
                  <SelectTrigger>
                    <SelectValue placeholder="Select range" />
                  </SelectTrigger>
                  <SelectContent>
                    {TIME_RANGE_OPTIONS.map((opt) => (
                      <SelectItem key={opt.value} value={opt.value}>
                        {opt.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-2">
                <div className="text-sm font-medium">Group By</div>
                <Select value={groupBy} onValueChange={setGroupBy}>
                  <SelectTrigger>
                    <SelectValue placeholder="Select grouping" />
                  </SelectTrigger>
                  <SelectContent>
                    {GROUP_BY_OPTIONS.map((opt) => (
                      <SelectItem key={opt.value} value={opt.value}>
                        {opt.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              {groupBy === "group" && (
                <div className="space-y-2">
                  <div className="text-sm font-medium">Device Group</div>
                  <Select value={selectedGroupId} onValueChange={setSelectedGroupId}>
                    <SelectTrigger>
                      <SelectValue placeholder="Select group" />
                    </SelectTrigger>
                    <SelectContent>
                      {groups.map((g) => (
                        <SelectItem key={g.group_id} value={g.group_id}>
                          {g.name}
                        </SelectItem>
                      ))}
                      {groups.length === 0 && (
                        <SelectItem value="__none__" disabled>
                          No groups found
                        </SelectItem>
                      )}
                    </SelectContent>
                  </Select>
                </div>
              )}

              {/* Device filter - only show when group_by is not "device" to avoid confusion */}
              {groupBy !== "device" && (
                <div className="space-y-1">
                  <label className="text-sm font-medium">Filter Devices</label>
                  <div className="max-h-40 overflow-auto border rounded p-2 space-y-1">
                    {devices.map((d) => (
                      <label
                        key={d.device_id}
                        className="flex items-center gap-2 text-sm cursor-pointer"
                      >
                        <input
                          type="checkbox"
                          checked={selectedDeviceIds.includes(d.device_id)}
                          onChange={(e) => {
                            if (e.target.checked) {
                              setSelectedDeviceIds((prev) => [...prev, d.device_id]);
                            } else {
                              setSelectedDeviceIds((prev) =>
                                prev.filter((id) => id !== d.device_id)
                              );
                            }
                          }}
                        />
                        <span className="truncate">{d.device_id}</span>
                      </label>
                    ))}
                    {devices.length === 0 && (
                      <div className="text-sm text-muted-foreground">No devices found</div>
                    )}
                  </div>
                  {selectedDeviceIds.length > 0 && (
                    <Button
                      variant="ghost"
                      size="sm"
                      className="h-8 text-sm"
                      onClick={() => setSelectedDeviceIds([])}
                    >
                      Clear selection ({selectedDeviceIds.length})
                    </Button>
                  )}
                </div>
              )}

              <Button
                className="w-full"
                onClick={handleRunQuery}
                disabled={!metric || queryMutation.isPending}
              >
                {queryMutation.isPending ? (
                  <>
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    Running...
                  </>
                ) : (
                  <>
                    <Play className="h-4 w-4 mr-2" />
                    Run Query
                  </>
                )}
              </Button>

              {queryMutation.isError && (
                <div className="rounded border border-destructive/30 bg-destructive/10 p-2 text-sm text-destructive">
                  Query failed. Adjust filters and try again.
                </div>
              )}
            </CardContent>
          </Card>
        </div>

        {/* Results */}
        <div className="flex-1 space-y-4 min-w-0">
          {!results ? (
            <div className="text-center py-8 text-muted-foreground">
              Select a metric and run a query to see results.
            </div>
          ) : (
            <>
              {results.summary && (
                <div className="grid grid-cols-4 gap-4">
                  <Card>
                    <CardContent className="pt-4">
                      <div className="text-sm text-muted-foreground">Min</div>
                      <div className="text-2xl font-semibold">
                        {results.summary.min?.toFixed(2) ?? "--"}
                      </div>
                    </CardContent>
                  </Card>
                  <Card>
                    <CardContent className="pt-4">
                      <div className="text-sm text-muted-foreground">Max</div>
                      <div className="text-2xl font-semibold">
                        {results.summary.max?.toFixed(2) ?? "--"}
                      </div>
                    </CardContent>
                  </Card>
                  <Card>
                    <CardContent className="pt-4">
                      <div className="text-sm text-muted-foreground">Avg</div>
                      <div className="text-2xl font-semibold">
                        {results.summary.avg?.toFixed(2) ?? "--"}
                      </div>
                    </CardContent>
                  </Card>
                  <Card>
                    <CardContent className="pt-4">
                      <div className="text-sm text-muted-foreground">Data Points</div>
                      <div className="text-2xl font-semibold">
                        {results.summary.total_points.toLocaleString()}
                      </div>
                    </CardContent>
                  </Card>
                </div>
              )}

              <Card>
                <CardHeader>
                  <CardTitle className="text-sm">Chart</CardTitle>
                </CardHeader>
                <CardContent>
                  {chartOption ? (
                    <EChartWrapper option={chartOption} style={{ height: 400 }} />
                  ) : (
                    <div className="text-sm text-muted-foreground py-10 text-center">
                      No data for this query.
                    </div>
                  )}
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle className="text-sm">Raw Data</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="max-h-64 overflow-auto">
                    <DataTable
                      columns={rawTableColumns}
                      data={queryResult?.rows ?? []}
                      isLoading={queryMutation.isPending}
                      emptyState={
                        <div className="rounded-lg border border-border py-8 text-center text-muted-foreground">
                          Run a query to see results.
                        </div>
                      }
                      manualPagination={false}
                    />
                  </div>
                </CardContent>
              </Card>
            </>
          )}
        </div>
      </div>
    </div>
  );
}

