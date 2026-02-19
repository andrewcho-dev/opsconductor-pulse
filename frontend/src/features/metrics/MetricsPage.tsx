import { useMemo, useState } from "react";
import { Activity, AlertTriangle, RefreshCcw } from "lucide-react";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { PageHeader, EmptyState } from "@/components/shared";
import { useMetricReference } from "@/hooks/use-metrics";
import type { NormalizedMetricReference } from "@/services/api/types";
import NormalizedMetricDialog from "./NormalizedMetricDialog";
import MapMetricDialog from "./MapMetricDialog";

export default function MetricsPage() {
  // Phase 172: this page is deprecated in favor of template-driven metric definitions.
  const canEdit = false;
  const { data, isLoading, error, refetch, isFetching } = useMetricReference();
  const [selectedNormalized, setSelectedNormalized] =
    useState<NormalizedMetricReference | null>(null);
  const [createNormalizedOpen, setCreateNormalizedOpen] = useState(false);
  const [mapRawMetric, setMapRawMetric] = useState<string | null>(null);

  const normalizedMetrics = useMemo(
    () =>
      Array.isArray(data?.normalized_metrics) ? data.normalized_metrics : [],
    [data]
  );
  const unmapped = useMemo(
    () => (Array.isArray(data?.unmapped) ? data.unmapped : []),
    [data]
  );

  return (
    <div className="space-y-4">
      <PageHeader
        title="Metrics"
        description={
          isLoading
            ? "Loading..."
            : `${normalizedMetrics.length} normalized metrics configured`
        }
      />
      <div className="mb-6 rounded-lg border border-yellow-200 bg-yellow-50 p-4 dark:border-yellow-800 dark:bg-yellow-950">
        <div className="flex items-center gap-2">
          <AlertTriangle className="h-5 w-5 text-yellow-600 dark:text-yellow-400" />
          <h3 className="font-semibold text-yellow-800 dark:text-yellow-200">Legacy Page</h3>
        </div>
        <p className="mt-1 text-sm text-yellow-700 dark:text-yellow-300">
          Metric definitions are now managed through{" "}
          <a href="/app/templates" className="underline font-medium">
            Device Templates
          </a>
          . This page shows legacy metric catalog and normalized metrics for reference only. No new
          entries should be created here.
        </p>
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
      ) : (
        <div className="space-y-8">
          <div className="space-y-3">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div>
                <h2 className="text-base font-semibold">Normalized Metrics</h2>
                <p className="text-sm text-muted-foreground">
                  Canonical metrics used in alert rules.
                </p>
              </div>
              <span className="text-xs text-muted-foreground">Read-only</span>
            </div>
            {normalizedMetrics.length === 0 ? (
              <EmptyState
                title="No normalized metrics yet"
                description="Create a normalized metric to group raw telemetry values."
                icon={<Activity className="h-12 w-12" />}
              />
            ) : (
              <div className="rounded-md border border-border">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Name</TableHead>
                      <TableHead>Unit</TableHead>
                      <TableHead>Mapped From</TableHead>
                      <TableHead className="text-right">Actions</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {normalizedMetrics.map((metric) => (
                      <TableRow key={metric.name}>
                        <TableCell>{metric.name}</TableCell>
                        <TableCell>{metric.display_unit || "—"}</TableCell>
                        <TableCell>
                          {metric.mapped_from.length > 0
                            ? metric.mapped_from.join(", ")
                            : "—"}
                        </TableCell>
                        <TableCell className="text-right">
                          {canEdit ? (
                            <Button
                              variant="outline"
                              size="sm"
                              onClick={() => setSelectedNormalized(metric)}
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
          </div>

          <div className="space-y-3">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div>
                <h2 className="text-base font-semibold">
                  Unmapped Raw Metrics ({unmapped.length} discovered)
                </h2>
                <p className="text-sm text-muted-foreground">
                  Map raw telemetry metrics to normalized names.
                </p>
              </div>
              <Button
                variant="outline"
                size="sm"
                onClick={() => refetch()}
                disabled={isFetching}
              >
                <RefreshCcw className="mr-2 h-4 w-4" />
                Refresh
              </Button>
            </div>
            {unmapped.length === 0 ? (
              <EmptyState
                title="No unmapped metrics"
                description="All discovered metrics are mapped."
                icon={<Activity className="h-12 w-12" />}
              />
            ) : (
              <div className="rounded-md border border-border">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Raw Metric</TableHead>
                      <TableHead>Map To</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {unmapped.map((metricName) => (
                      <TableRow key={metricName}>
                        <TableCell className="font-mono text-sm">{metricName}</TableCell>
                        <TableCell>
                          {canEdit ? (
                            <Button
                              variant="outline"
                              size="sm"
                              onClick={() => setMapRawMetric(metricName)}
                            >
                              Map to...
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
          </div>
        </div>
      )}

      <NormalizedMetricDialog
        open={createNormalizedOpen}
        metric={null}
        onClose={() => setCreateNormalizedOpen(false)}
      />
      <NormalizedMetricDialog
        open={!!selectedNormalized}
        metric={selectedNormalized}
        onClose={() => setSelectedNormalized(null)}
      />
      <MapMetricDialog
        open={!!mapRawMetric}
        rawMetric={mapRawMetric}
        normalizedMetrics={normalizedMetrics}
        onClose={() => setMapRawMetric(null)}
      />
    </div>
  );
}
