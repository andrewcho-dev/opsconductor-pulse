import { useEffect, useMemo, useState } from "react";
import { Skeleton } from "@/components/ui/skeleton";
import { PageHeader, EmptyState } from "@/components/shared";
import { Badge } from "@/components/ui/badge";
import { useAlerts } from "@/hooks/use-alerts";
import { acknowledgeAlert, closeAlert, silenceAlert } from "@/services/api/alerts";
import { Bell, ChevronDown, ChevronRight, RefreshCw } from "lucide-react";
import { useQueryClient } from "@tanstack/react-query";
import { Link } from "react-router-dom";

const SILENCE_OPTIONS = [
  { label: "15m", value: 15 },
  { label: "1h", value: 60 },
  { label: "4h", value: 240 },
  { label: "24h", value: 1440 },
] as const;

const TABS = [
  { key: "ALL", label: "All" },
  { key: "OPEN:CRITICAL", label: "Critical" },
  { key: "OPEN:HIGH", label: "High" },
  { key: "OPEN:MEDIUM", label: "Medium" },
  { key: "OPEN:LOW", label: "Low" },
  { key: "ACKNOWLEDGED", label: "Ack'd" },
  { key: "CLOSED", label: "Closed" },
] as const;

type TabKey = (typeof TABS)[number]["key"];

function levelFromSeverity(severity: number): "CRITICAL" | "HIGH" | "MEDIUM" | "LOW" {
  if (severity >= 5) return "CRITICAL";
  if (severity >= 4) return "HIGH";
  if (severity >= 3) return "MEDIUM";
  return "LOW";
}

function severityDotClass(severity: number) {
  const level = levelFromSeverity(severity);
  if (level === "CRITICAL") return "bg-red-500";
  if (level === "HIGH") return "bg-orange-500";
  if (level === "MEDIUM") return "bg-yellow-500";
  return "bg-blue-500";
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

export default function AlertListPage() {
  const queryClient = useQueryClient();
  const [tab, setTab] = useState<TabKey>("ALL");
  const [search, setSearch] = useState("");
  const [selected, setSelected] = useState<Set<number>>(new Set());
  const [expandedAlertId, setExpandedAlertId] = useState<number | null>(null);
  const [now, setNow] = useState(Date.now());
  const { data, isLoading, error, refetch, isFetching } = useAlerts("ALL", 500, 0);

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
    const base = {
      ALL: allAlerts.length,
      "OPEN:CRITICAL": 0,
      "OPEN:HIGH": 0,
      "OPEN:MEDIUM": 0,
      "OPEN:LOW": 0,
      ACKNOWLEDGED: 0,
      CLOSED: 0,
    };
    for (const alert of allAlerts) {
      if (alert.status === "ACKNOWLEDGED") base.ACKNOWLEDGED += 1;
      if (alert.status === "CLOSED") base.CLOSED += 1;
      if (alert.status === "OPEN") {
        const level = levelFromSeverity(alert.severity);
        base[`OPEN:${level}`] += 1;
      }
    }
    return base;
  }, [allAlerts]);

  const filteredAlerts = useMemo(() => {
    const byTab = allAlerts.filter((alert) => {
      if (tab === "ALL") return true;
      if (tab === "ACKNOWLEDGED" || tab === "CLOSED") return alert.status === tab;
      const [status, level] = tab.split(":");
      return alert.status === status && levelFromSeverity(alert.severity) === level;
    });
    const query = search.trim().toLowerCase();
    if (!query) return byTab;
    return byTab.filter((alert) => {
      return (
        alert.device_id.toLowerCase().includes(query) ||
        alert.alert_type.toLowerCase().includes(query)
      );
    });
  }, [allAlerts, tab, search]);

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
    <div className="space-y-6">
      <PageHeader
        title="Alerts"
        description="Professional inbox for real-time alert triage"
        action={
          <div className="flex items-center gap-2">
            <button
              onClick={() => refetch()}
              className="inline-flex items-center gap-1 rounded border border-border px-3 py-1.5 text-sm hover:bg-accent"
            >
              <RefreshCw className={`h-3.5 w-3.5 ${isFetching ? "animate-spin" : ""}`} />
              Refresh
            </button>
            <Link
              to="/alert-rules"
              className="rounded border border-border px-3 py-1.5 text-sm hover:bg-accent"
            >
              Rules
            </Link>
          </div>
        }
      />

      <div className="flex flex-wrap gap-2">
        {TABS.map((item) => (
          <button
            key={item.key}
            onClick={() => {
              setTab(item.key);
              setSearch("");
              setSelected(new Set());
            }}
            className={`px-3 py-1.5 text-sm rounded-md border transition-colors ${
              tab === item.key
                ? "bg-primary text-primary-foreground border-primary"
                : "border-border text-muted-foreground hover:bg-accent"
            }`}
          >
            {item.label}
            <span className="ml-2 rounded bg-background/70 px-1.5 py-0.5 text-xs">
              {counts[item.key]}
            </span>
          </button>
        ))}
      </div>

      <div className="flex flex-wrap items-center justify-between gap-2 rounded-md border border-border p-3">
        <div className="flex items-center gap-2">
          {selected.size > 0 && (
            <>
              <button
                onClick={() => runBulk("ack")}
                className="rounded border border-border px-2 py-1 text-xs hover:bg-accent"
              >
                Ack Selected
              </button>
              <button
                onClick={() => runBulk("close")}
                className="rounded border border-border px-2 py-1 text-xs hover:bg-accent"
              >
                Close Selected
              </button>
            </>
          )}
          {selected.size === 0 && (
            <span className="text-xs text-muted-foreground">Select alerts for bulk actions</span>
          )}
        </div>
        <input
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search device or alert type..."
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
          <div className="grid grid-cols-[40px_40px_170px_1fr_170px_100px_60px] border-b border-border bg-muted/30 px-2 py-2 text-xs font-semibold uppercase text-muted-foreground">
            <div>
              <input
                type="checkbox"
                checked={allVisibleSelected}
                onChange={(e) => toggleAllVisible(e.target.checked)}
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
                    <input
                      type="checkbox"
                      checked={selected.has(alert.alert_id)}
                      onChange={(e) => toggleSelected(alert.alert_id, e.target.checked)}
                    />
                  </div>
                  <button
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
                  </button>
                  <div className="flex items-center gap-2">
                    <span className={`h-2.5 w-2.5 rounded-full ${severityDotClass(alert.severity)}`} />
                    <span>{levelFromSeverity(alert.severity)}</span>
                  </div>
                  <div>
                    <div className="font-medium">{alert.device_id}</div>
                    <div className="text-xs text-muted-foreground">{alert.alert_type}</div>
                  </div>
                  <div className="text-xs text-muted-foreground">
                    {formatTimeAgo(alert.created_at)}
                  </div>
                  <div>
                    <Badge variant="outline">{alert.status}</Badge>
                  </div>
                  <details className="relative">
                    <summary className="cursor-pointer list-none text-center">···</summary>
                    <div className="absolute right-0 z-10 mt-1 w-36 rounded border border-border bg-background p-1 shadow-md">
                      <button
                        onClick={async () => {
                          await acknowledgeAlert(String(alert.alert_id));
                          await refreshAlerts();
                        }}
                        className="block w-full rounded px-2 py-1 text-left text-xs hover:bg-accent"
                      >
                        Acknowledge
                      </button>
                      <button
                        onClick={async () => {
                          await closeAlert(String(alert.alert_id));
                          await refreshAlerts();
                        }}
                        className="block w-full rounded px-2 py-1 text-left text-xs hover:bg-accent"
                      >
                        Close
                      </button>
                      {SILENCE_OPTIONS.map((opt) => (
                        <button
                          onClick={async () => {
                            await silenceAlert(String(alert.alert_id), opt.value);
                            await refreshAlerts();
                          }}
                          key={opt.value}
                          className="block w-full rounded px-2 py-1 text-left text-xs hover:bg-accent"
                        >
                          Silence {opt.label}
                        </button>
                      ))}
                      <Link
                        to={`/devices/${alert.device_id}`}
                        className="block rounded px-2 py-1 text-left text-xs hover:bg-accent"
                      >
                        View Device
                      </Link>
                    </div>
                  </details>
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
                    </div>
                    <div className="mt-3">
                      <div className="mb-1 text-xs text-muted-foreground">Summary</div>
                      <p>{alert.summary}</p>
                    </div>
                    <div className="mt-3">
                      <div className="mb-1 text-xs text-muted-foreground">Details</div>
                      <pre className="max-h-32 overflow-auto rounded bg-muted p-2 text-xs">
                        {JSON.stringify(alert.details ?? {}, null, 2)}
                      </pre>
                    </div>
                    <div className="mt-3 flex flex-wrap items-center gap-2">
                      <button
                        onClick={async () => {
                          await acknowledgeAlert(String(alert.alert_id));
                          await refreshAlerts();
                        }}
                        className="rounded border border-border px-2 py-1 text-xs hover:bg-accent"
                      >
                        Acknowledge
                      </button>
                      <button
                        onClick={async () => {
                          await closeAlert(String(alert.alert_id));
                          await refreshAlerts();
                        }}
                        className="rounded border border-border px-2 py-1 text-xs hover:bg-accent"
                      >
                        Close
                      </button>
                      {SILENCE_OPTIONS.map((opt) => (
                        <button
                          key={opt.value}
                          onClick={async () => {
                            await silenceAlert(String(alert.alert_id), opt.value);
                            await refreshAlerts();
                          }}
                          className="rounded border border-border px-2 py-1 text-xs hover:bg-accent"
                        >
                          Silence {opt.label}
                        </button>
                      ))}
                      <Link
                        to={`/devices/${alert.device_id}`}
                        className="rounded border border-border px-2 py-1 text-xs hover:bg-accent"
                      >
                        View Device →
                      </Link>
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
