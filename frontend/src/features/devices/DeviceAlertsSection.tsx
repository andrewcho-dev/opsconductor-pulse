import { Link } from "react-router-dom";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { SeverityBadge } from "@/components/shared";
import { useDeviceAlerts } from "@/hooks/use-device-alerts";
import { acknowledgeAlert, closeAlert, silenceAlert } from "@/services/api/alerts";
import { useQueryClient } from "@tanstack/react-query";
import { formatTimestamp } from "@/lib/format";
import { Bell } from "lucide-react";
import { memo, useState } from "react";

interface DeviceAlertsSectionProps {
  deviceId: string;
}

function DeviceAlertsSectionInner({ deviceId }: DeviceAlertsSectionProps) {
  const queryClient = useQueryClient();
  const { data, isLoading } = useDeviceAlerts(deviceId, "OPEN", 50);
  const alerts = data?.alerts || [];
  const [silenceForAlert, setSilenceForAlert] = useState<number | null>(null);
  const [silenceMinutes, setSilenceMinutes] = useState(30);

  const refresh = async () => {
    await queryClient.invalidateQueries({ queryKey: ["device-alerts"] });
    await queryClient.invalidateQueries({ queryKey: ["alerts"] });
  };

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between">
        <CardTitle className="text-lg">Device Alerts</CardTitle>
        <Link
          to="/alerts"
          className="text-sm text-primary hover:underline"
        >
          View all alerts
        </Link>
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <div className="space-y-2">
            {[1, 2, 3].map((i) => (
              <Skeleton key={i} className="h-8 w-full" />
            ))}
          </div>
        ) : alerts.length === 0 ? (
          <div className="flex flex-col items-center py-6 text-center">
            <Bell className="h-6 w-6 text-muted-foreground mb-2" />
            <p className="text-sm text-muted-foreground">
              No open alerts for this device
            </p>
          </div>
        ) : (
          <div className="space-y-1">
            {alerts.map((a) => (
              <div
                key={a.alert_id}
                className={`flex items-center gap-3 py-2 px-2 rounded-md hover:bg-accent/50 transition-colors text-sm ${
                  a.status === "ACKNOWLEDGED" ? "opacity-60" : ""
                }`}
              >
                <SeverityBadge severity={a.severity} className="shrink-0" />
                <span className="truncate flex-1">{a.summary}</span>
                <span className="text-sm text-muted-foreground shrink-0">
                  {a.alert_type}
                </span>
                <span className="text-xs text-muted-foreground shrink-0 hidden md:inline">
                  {formatTimestamp(a.created_at)}
                </span>
                {a.status === "OPEN" && (
                  <button
                    onClick={async () => {
                      await acknowledgeAlert(String(a.alert_id));
                      await refresh();
                    }}
                    className="px-2 py-1 rounded border border-border text-sm hover:bg-accent"
                  >
                    Ack
                  </button>
                )}
                {(a.status === "OPEN" || a.status === "ACKNOWLEDGED") && (
                  <>
                    <button
                      onClick={async () => {
                        await closeAlert(String(a.alert_id));
                        await refresh();
                      }}
                      className="px-2 py-1 rounded border border-border text-sm hover:bg-accent"
                    >
                      Close
                    </button>
                    <button
                      onClick={() => setSilenceForAlert(a.alert_id)}
                      className="px-2 py-1 rounded border border-border text-sm hover:bg-accent"
                    >
                      Silence
                    </button>
                    {silenceForAlert === a.alert_id && (
                      <>
                        <select
                          value={silenceMinutes}
                          onChange={(e) => setSilenceMinutes(Number(e.target.value))}
                          className="px-2 py-1 text-sm rounded border border-border bg-background"
                        >
                          <option value={15}>15m</option>
                          <option value={30}>30m</option>
                          <option value={60}>1h</option>
                          <option value={240}>4h</option>
                          <option value={1440}>24h</option>
                        </select>
                        <button
                          onClick={async () => {
                            await silenceAlert(String(a.alert_id), silenceMinutes);
                            setSilenceForAlert(null);
                            await refresh();
                          }}
                          className="px-2 py-1 rounded border border-border text-sm hover:bg-accent"
                        >
                          Apply
                        </button>
                      </>
                    )}
                  </>
                )}
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

export const DeviceAlertsSection = memo(DeviceAlertsSectionInner);
