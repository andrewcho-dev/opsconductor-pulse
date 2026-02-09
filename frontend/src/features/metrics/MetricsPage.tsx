import { useMemo, useState } from "react";
import { Activity, RefreshCcw } from "lucide-react";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { PageHeader, EmptyState } from "@/components/shared";
import { useAuth } from "@/services/auth/AuthProvider";
import { useMetrics } from "@/hooks/use-metrics";
import type { MetricReference } from "@/services/api/types";
import MetricEditDialog from "./MetricEditDialog";

export default function MetricsPage() {
  const { user } = useAuth();
  const canEdit = user?.role === "customer_admin";
  const { data, isLoading, error, refetch, isFetching } = useMetrics();
  const [search, setSearch] = useState("");
  const [selectedMetric, setSelectedMetric] = useState<MetricReference | null>(null);

  const metrics = useMemo(() => data ?? [], [data]);
  const filteredMetrics = useMemo(() => {
    const trimmed = search.trim().toLowerCase();
    if (!trimmed) return metrics;
    return metrics.filter((metric) => metric.name.toLowerCase().includes(trimmed));
  }, [metrics, search]);

  return (
    <div className="space-y-6">
      <PageHeader
        title="Metrics"
        description={
          isLoading ? "Loading..." : `${metrics.length} metrics discovered from your devices`
        }
        action={
          <Button variant="outline" size="sm" onClick={() => refetch()} disabled={isFetching}>
            <RefreshCcw className="mr-2 h-4 w-4" />
            Refresh
          </Button>
        }
      />

      <div className="flex items-center gap-2">
        <Input
          value={search}
          onChange={(event) => setSearch(event.target.value)}
          placeholder="Search metrics"
          className="max-w-sm"
        />
      </div>

      {error ? (
        <div className="text-destructive">
          Failed to load metrics: {(error as Error).message}
        </div>
      ) : isLoading ? (
        <div className="space-y-2">
          {[1, 2, 3, 4, 5].map((i) => (
            <Skeleton key={i} className="h-10 w-full" />
          ))}
        </div>
      ) : filteredMetrics.length === 0 ? (
        <EmptyState
          title="No metrics found"
          description="Metrics will appear after devices send telemetry."
          icon={<Activity className="h-12 w-12" />}
        />
      ) : (
        <div className="rounded-md border border-border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Metric Name</TableHead>
                <TableHead>Description</TableHead>
                <TableHead>Unit</TableHead>
                <TableHead>Range</TableHead>
                <TableHead className="text-right">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {filteredMetrics.map((metric) => (
                <TableRow key={metric.name}>
                  <TableCell className="font-mono text-sm">{metric.name}</TableCell>
                  <TableCell>{metric.description || "—"}</TableCell>
                  <TableCell>{metric.unit || "—"}</TableCell>
                  <TableCell>{metric.range || "—"}</TableCell>
                  <TableCell className="text-right">
                    {canEdit ? (
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => setSelectedMetric(metric)}
                      >
                        Edit
                      </Button>
                    ) : (
                      <span className="text-xs text-muted-foreground">Read-only</span>
                    )}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}

      <MetricEditDialog
        open={!!selectedMetric}
        metric={selectedMetric}
        onClose={() => setSelectedMetric(null)}
        canEdit={canEdit}
      />
    </div>
  );
}
