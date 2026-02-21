import { useEffect, useMemo, useState } from "react";
import { Skeleton } from "@/components/ui/skeleton";
import { PageHeader, EmptyState } from "@/components/shared";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { useAlerts } from "@/hooks/use-alerts";
import { acknowledgeAlert, closeAlert, silenceAlert } from "@/services/api/alerts";
import { Bell, ChevronDown, ChevronRight, MoreHorizontal, RefreshCw } from "lucide-react";
import { useQueryClient } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";

const SILENCE_OPTIONS = [
  { label: "15m", value: 15 },
  { label: "1h", value: 60 },
  { label: "4h", value: 240 },
  { label: "24h", value: 1440 },
] as const;

const TABS = [
  { key: "ALL", label: "All" },
  { key: "CRITICAL", label: "Critical" },
  { key: "HIGH", label: "High" },
  { key: "MEDIUM", label: "Medium" },
  { key: "LOW", label: "Low" },
  { key: "ACKNOWLEDGED", label: "Ack'd" },
  { key: "CLOSED", label: "Closed" },
] as const;

type TabKey = (typeof TABS)[number]["key"];
type SeverityLevel = "CRITICAL" | "HIGH" | "MEDIUM" | "LOW";

const TAB_CONFIG: Record<
  TabKey,
  { apiStatus: "OPEN" | "ACKNOWLEDGED" | "CLOSED"; severity?: SeverityLevel }
> = {
  ALL: { apiStatus: "OPEN" },
  CRITICAL: { apiStatus: "OPEN", severity: "CRITICAL" },
  HIGH: { apiStatus: "OPEN", severity: "HIGH" },
  MEDIUM: { apiStatus: "OPEN", severity: "MEDIUM" },
  LOW: { apiStatus: "OPEN", severity: "LOW" },
  ACKNOWLEDGED: { apiStatus: "ACKNOWLEDGED" },
  CLOSED: { apiStatus: "CLOSED" },
};

function levelFromSeverity(severity: number): SeverityLevel {
  if (severity >= 5) return "CRITICAL";
  if (severity >= 4) return "HIGH";
  if (severity >= 3) return "MEDIUM";
  return "LOW";
}

function severityDotClass(severity: number) {
  const level = levelFromSeverity(severity);
  if (level === "CRITICAL") return "bg-status-critical";
  if (level === "HIGH") return "bg-status-warning";
  if (level === "MEDIUM") return "bg-status-stale";
  return "bg-status-info";
}

function formatTimeAgo(input: string) {
  const deltaMs = Date.now() - new Date(input).getTime();
  if (!Number.isFinite(deltaMs) || deltaMs < 0) return "just now";
  const mins = Math.floor(deltaMs / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  return `${Math.floor(hours / 24)}d ago`;
}

function formatDuration(from: string, now: number) {
  const deltaSec = Math.max(0, Math.floor((now - new Date(from).getTime()) / 1000));
  const hours = Math.floor(deltaSec / 3600);
  const minutes = Math.floor((deltaSec % 3600) / 60);
  const seconds = deltaSec % 60;
  if (hours > 0) return `${hours}h ${minutes}m`;
  if (minutes > 0) return `${minutes}m ${seconds}s`;
  return `${seconds}s`;
}

export default function AlertListPage({ embedded }: { embedded?: boolean }) {
  const queryClient = useQueryClient();
  const [tab, setTab] = useState<TabKey>("ALL");
  const [search, setSearch] = useState("");
  const [selected, setSelected] = useState<Set<number>>(new Set());
  const [expandedAlertId, setExpandedAlertId] = useState<number | null>(null);
  const [now, setNow] = useState(Date.now());
  const [pageSize, setPageSize] = useState(25);
  const [pageIndex, setPageIndex] = useState(0);
  const activeApiStatus = TAB_CONFIG[tab].apiStatus;
  const activeSeverity = TAB_CONFIG[tab].severity;
  const { data, isLoading, error, refetch, isFetching } = useAlerts(
    activeApiStatus,
    pageSize,
    pageIndex * pageSize
  );
  const { data: allOpenData } = useAlerts("OPEN", 1, 0);
  const { data: ackData } = useAlerts("ACKNOWLEDGED", 1, 0);
  const { data: closedData } = useAlerts("CLOSED", 1, 0);

  useEffect(() => {
    const timer = window.setInterval(() => setNow(Date.now()), 1000);
    return () => window.clearInterval(timer);
  }, []);

  const refreshAlerts = async () => {
    await queryClient.invalidateQueries({ queryKey: ["alerts"] });
    await queryClient.invalidateQueries({ queryKey: ["device-alerts"] });
  };

  const allAlerts = data?.alerts ?? [];
  const counts = useMemo(() => {
    return {
      ALL: (allOpenData?.total ?? 0) + (ackData?.total ?? 0) + (closedData?.total ?? 0),
      CRITICAL: 0,
      HIGH: 0,
      MEDIUM: 0,
      LOW: 0,
      ACKNOWLEDGED: ackData?.total ?? 0,
      CLOSED: closedData?.total ?? 0,
    };
  }, [allOpenData?.total, ackData?.total, closedData?.total]);

  const filteredAlerts = useMemo(() => {
    const byTab = activeSeverity
      ? allAlerts.filter((alert) => levelFromSeverity(alert.severity) === activeSeverity)
      : allAlerts;
    const query = search.trim().toLowerCase();
    if (!query) return byTab;
    return byTab.filter((alert) => {
      return (
        alert.device_id.toLowerCase().includes(query) ||
        alert.alert_type.toLowerCase().includes(query)
      );
    });
  }, [allAlerts, activeSeverity, search]);

  const allVisibleSelected =
    filteredAlerts.length > 0 &&
    filteredAlerts.every((alert) => selected.has(alert.alert_id));

  const toggleAllVisible = (checked: boolean) => {
    const next = new Set(selected);
    for (const alert of filteredAlerts) {
      if (checked) next.add(alert.alert_id);
      else next.delete(alert.alert_id);
    }
    setSelected(next);
  };

  const toggleSelected = (alertId: number, checked: boolean) => {
    const next = new Set(selected);
    if (checked) next.add(alertId);
    else next.delete(alertId);
    setSelected(next);
  };

  const runBulk = async (action: "ack" | "close") => {
    for (const alertId of selected) {
      if (action === "ack") await acknowledgeAlert(String(alertId));
      else await closeAlert(String(alertId));
    }
    setSelected(new Set());
    await refreshAlerts();
  };

  return (
    <div className="space-y-4">
      <div role="status" aria-live="polite" aria-atomic="true" className="sr-only">
        {filteredAlerts.length} alerts loaded
      </div>
      {!embedded && (
        <PageHeader
          title="Alerts"
          description="Professional inbox for real-time alert triage"
          action={
            <div className="flex items-center gap-2">
              <Button variant="outline" size="sm" onClick={() => refetch()}>
                <RefreshCw
                  className={`mr-1 h-3.5 w-3.5 ${isFetching ? "animate-spin" : ""}`}
                />
                Refresh
              </Button>
              <Button variant="outline" size="sm" asChild>
                <Link to="/alert-rules">Rules</Link>
              </Button>
            </div>
          }
        />
      )}

      <div className="flex flex-wrap gap-2">
        {TABS.map((item) => (
          <Button
            key={item.key}
            variant={tab === item.key ? "default" : "outline"}
            size="sm"
            onClick={() => {
              setTab(item.key);
              setSearch("");
              setSelected(new Set());
              setPageIndex(0);
            }}
          >
            {item.label}
            <span className="ml-2 rounded bg-background/70 px-1.5 py-0.5 text-xs">
              {counts[item.key]}
            </span>
          </Button>
        ))}
      </div>

      <div className="flex flex-wrap items-center justify-between gap-2 rounded-md border border-border p-3">
        <div className="flex items-center gap-2">
          {selected.size > 0 && (
            <>
              <Button variant="outline" size="sm" onClick={() => runBulk("ack")}>
                Acknowledge Selected ({selected.size})
              </Button>
              <Button variant="outline" size="sm" onClick={() => runBulk("close")}>
                Close Selected ({selected.size})
              </Button>
            </>
          )}
          {selected.size === 0 && (
            <span className="text-sm text-muted-foreground">Select alerts for bulk actions</span>
          )}
        </div>
        <input
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search device or alert type..."
          aria-label="Search alerts"
          className="h-8 w-full max-w-xs rounded border border-border bg-background px-2 text-sm"
        />
      </div>

      {error ? (
        <div className="text-destructive">
          Failed to load alerts: {(error as Error).message}
        </div>
      ) : isLoading ? (
        <div className="space-y-2">
          {[1, 2, 3, 4, 5].map((i) => (
            <Skeleton key={i} className="h-12 w-full" />
          ))}
        </div>
      ) : filteredAlerts.length === 0 ? (
        <EmptyState
          title="No alerts match this view"
          description="Alerts appear when devices trigger threshold rules or miss heartbeats."
          icon={<Bell className="h-12 w-12" />}
        />
      ) : (
        <div className="rounded-md border border-border">
          <div className="grid grid-cols-[40px_40px_170px_1fr_170px_100px_60px] border-b border-border bg-muted/30 px-2 py-2 text-sm font-semibold uppercase text-muted-foreground">
            <div>
              <Checkbox
                checked={allVisibleSelected}
                onCheckedChange={(checked) => toggleAllVisible(checked === true)}
              />
            </div>
            <div />
            <div>Severity</div>
            <div>Device / Type</div>
            <div>Time</div>
            <div>Status</div>
            <div className="text-center">···</div>
          </div>

          {filteredAlerts.map((alert) => {
            const isExpanded = expandedAlertId === alert.alert_id;
            return (
              <div key={alert.alert_id} className="border-b border-border last:border-b-0">
                <div className="grid grid-cols-[40px_40px_170px_1fr_170px_100px_60px] items-center px-2 py-2 text-sm">
                  <div>
                    <Checkbox
                      checked={selected.has(alert.alert_id)}
                      onCheckedChange={(checked) => toggleSelected(alert.alert_id, checked === true)}
                    />
                  </div>
                  <Button
                    variant="ghost"
                    size="icon"
                    aria-label={isExpanded ? "Collapse alert details" : "Expand alert details"}
                    onClick={() =>
                      setExpandedAlertId(isExpanded ? null : alert.alert_id)
                    }
                    className="text-muted-foreground"
                  >
                    {isExpanded ? (
                      <ChevronDown className="h-4 w-4" />
                    ) : (
                      <ChevronRight className="h-4 w-4" />
                    )}
                  </Button>
                  <div className="flex items-center gap-2">
                    <span className={`h-2.5 w-2.5 rounded-full ${severityDotClass(alert.severity)}`} />
                    <span>{levelFromSeverity(alert.severity)}</span>
                  </div>
                  <div>
                    <div className="font-medium">{alert.device_id}</div>
                    <div className="text-sm text-muted-foreground">
                      {alert.alert_type}
                      {alert.trigger_count && alert.trigger_count > 1 && (
                        <Badge variant="secondary" className="ml-2">
                          {alert.trigger_count}x
                        </Badge>
                      )}
                    </div>
                  </div>
                  <div className="text-sm text-muted-foreground">
                    {formatTimeAgo(alert.created_at)}
                    {alert.trigger_count &&
                      alert.trigger_count > 1 &&
                      alert.last_triggered_at && (
                        <div className="text-sm text-muted-foreground/70">
                          last: {formatTimeAgo(alert.last_triggered_at)}
                        </div>
                      )}
                  </div>
                  <div>
                    <Badge variant="outline">{alert.status}</Badge>
                  </div>
                  <DropdownMenu>
                    <DropdownMenuTrigger asChild>
                      <Button variant="ghost" size="sm" aria-label="Open alert actions">
                        <MoreHorizontal className="h-4 w-4" />
                      </Button>
                    </DropdownMenuTrigger>
                    <DropdownMenuContent align="end">
                      <DropdownMenuItem
                        onClick={async () => {
                          await acknowledgeAlert(String(alert.alert_id));
                          await refreshAlerts();
                        }}
                      >
                        Acknowledge
                      </DropdownMenuItem>
                      <DropdownMenuItem
                        onClick={async () => {
                          await closeAlert(String(alert.alert_id));
                          await refreshAlerts();
                        }}
                      >
                        Close
                      </DropdownMenuItem>
                      <DropdownMenuSeparator />
                      {SILENCE_OPTIONS.map((opt) => (
                        <DropdownMenuItem
                          key={opt.value}
                          onClick={async () => {
                            await silenceAlert(String(alert.alert_id), opt.value);
                            await refreshAlerts();
                          }}
                        >
                          Silence {opt.label}
                        </DropdownMenuItem>
                      ))}
                      {alert.device_id && (
                        <>
                          <DropdownMenuSeparator />
                          <DropdownMenuItem asChild>
                            <Link to={`/devices/${alert.device_id}`}>View Device</Link>
                          </DropdownMenuItem>
                        </>
                      )}
                    </DropdownMenuContent>
                  </DropdownMenu>
                </div>

                {isExpanded && (
                  <div className="mx-2 mb-2 rounded border border-border bg-muted/30 p-3 text-sm">
                    <div className="mb-2 font-semibold">Alert Details</div>
                    <div className="grid gap-2 md:grid-cols-2">
                      <div>Device: {alert.device_id}</div>
                      <div>Tenant: {alert.tenant_id}</div>
                      <div>Rule: {alert.summary || "—"}</div>
                      <div>Type: {alert.alert_type}</div>
                      <div>Opened: {new Date(alert.created_at).toLocaleString()}</div>
                      <div>Duration: {formatDuration(alert.created_at, now)}</div>
                      <div>
                        Silenced until:{" "}
                        {alert.silenced_until
                          ? new Date(alert.silenced_until).toLocaleString()
                          : "—"}
                      </div>
                      <div>Escalation level: {alert.escalation_level ?? 0}</div>
                      <div>
                        Triggered: {alert.trigger_count ?? 1} time
                        {(alert.trigger_count ?? 1) !== 1 ? "s" : ""}
                      </div>
                      <div>
                        Last triggered:{" "}
                        {alert.last_triggered_at
                          ? formatTimeAgo(alert.last_triggered_at)
                          : formatTimeAgo(alert.created_at)}
                      </div>
                    </div>
                    <div className="mt-3">
                      <div className="mb-1 text-sm text-muted-foreground">Summary</div>
                      <p>{alert.summary}</p>
                    </div>
                    <div className="mt-3">
                      <div className="mb-1 text-sm text-muted-foreground">Details</div>
                      <pre className="max-h-32 overflow-auto rounded bg-muted p-2 text-sm">
                        {JSON.stringify(alert.details ?? {}, null, 2)}
                      </pre>
                    </div>
                    <div className="mt-3 flex flex-wrap items-center gap-2">
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={async () => {
                          await acknowledgeAlert(String(alert.alert_id));
                          await refreshAlerts();
                        }}
                      >
                        Acknowledge
                      </Button>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={async () => {
                          await closeAlert(String(alert.alert_id));
                          await refreshAlerts();
                        }}
                      >
                        Close
                      </Button>
                      {SILENCE_OPTIONS.map((opt) => (
                        <Button
                          variant="outline"
                          size="sm"
                          key={opt.value}
                          onClick={async () => {
                            await silenceAlert(String(alert.alert_id), opt.value);
                            await refreshAlerts();
                          }}
                        >
                          Silence {opt.label}
                        </Button>
                      ))}
                      <Button variant="outline" size="sm" asChild>
                        <Link to={`/devices/${alert.device_id}`}>View Device</Link>
                      </Button>
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}

      {!isLoading && filteredAlerts.length > 0 && (
        <div className="flex items-center justify-between">
          <span className="text-sm text-muted-foreground">
            Showing {pageIndex * pageSize + 1}–
            {Math.min((pageIndex + 1) * pageSize, data?.total ?? 0)} of {data?.total ?? 0}
          </span>
          <div className="flex items-center gap-2">
            <Select
              value={String(pageSize)}
              onValueChange={(v) => {
                setPageSize(Number(v));
                setPageIndex(0);
              }}
            >
              <SelectTrigger className="h-8 w-[110px]">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {[10, 25, 50, 100].map((size) => (
                  <SelectItem key={size} value={String(size)}>
                    {size} / page
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <Button
              variant="outline"
              size="sm"
              onClick={() => setPageIndex((p) => Math.max(0, p - 1))}
              disabled={pageIndex === 0}
            >
              Previous
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => setPageIndex((p) => p + 1)}
              disabled={(pageIndex + 1) * pageSize >= (data?.total ?? 0)}
            >
              Next
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
