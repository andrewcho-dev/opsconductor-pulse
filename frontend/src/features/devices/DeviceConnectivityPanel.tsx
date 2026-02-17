import { useEffect, useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  fetchDeviceConnections,
  type ConnectionEvent,
  type ConnectionEventsResponse,
} from "@/services/api/devices";

interface DeviceConnectivityPanelProps {
  deviceId: string;
}

const EVENT_STYLES: Record<
  ConnectionEvent["event_type"],
  { label: string; variant: "default" | "secondary" | "destructive" | "outline" }
> = {
  CONNECTED: { label: "Connected", variant: "default" },
  DISCONNECTED: { label: "Disconnected", variant: "secondary" },
  CONNECTION_LOST: { label: "Connection Lost", variant: "destructive" },
};

export function DeviceConnectivityPanel({ deviceId }: DeviceConnectivityPanelProps) {
  const [data, setData] = useState<ConnectionEventsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadEvents = async (offset = 0) => {
    setLoading(true);
    setError(null);
    try {
      const result = await fetchDeviceConnections(deviceId, 50, offset);
      setData(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load connectivity events");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void loadEvents();
  }, [deviceId]);

  if (loading && !data) {
    return (
      <div className="rounded border border-border p-3 text-sm text-muted-foreground">
        Loading connectivity events...
      </div>
    );
  }

  return (
    <div className="rounded border border-border p-3 space-y-3">
      <div className="flex items-center justify-between">
        <h4 className="text-sm font-semibold">Connectivity Log</h4>
        <Button size="sm" variant="outline" onClick={() => void loadEvents()}>
          Refresh
        </Button>
      </div>

      {error && <div className="text-sm text-destructive">{error}</div>}

      {data && data.events.length === 0 && (
        <div className="text-sm text-muted-foreground">No connectivity events recorded yet.</div>
      )}

      {data && data.events.length > 0 && (
        <div className="space-y-2">
          {data.events.map((event) => {
            const style = EVENT_STYLES[event.event_type] ?? EVENT_STYLES.DISCONNECTED;
            const ts = new Date(event.timestamp);
            return (
              <div
                key={event.id}
                className="flex items-start gap-3 rounded border border-border p-2"
              >
                <Badge variant={style.variant} className="mt-0.5 shrink-0">
                  {style.label}
                </Badge>
                <div className="min-w-0 flex-1">
                  <div className="text-xs text-muted-foreground">{ts.toLocaleString()}</div>
                  {event.details && Object.keys(event.details).length > 0 && (
                    <div className="mt-1 text-sm text-muted-foreground">
                      {Object.entries(event.details)
                        .filter(([, v]) => v != null)
                        .map(([k, v]) => `${k}: ${String(v)}`)
                        .join(" | ")}
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}

      {data && data.total > data.events.length + (data.offset ?? 0) && (
        <Button
          size="sm"
          variant="outline"
          onClick={() => void loadEvents((data.offset ?? 0) + data.events.length)}
        >
          Load more
        </Button>
      )}

      {data && (
        <div className="text-xs text-muted-foreground">
          Showing {data.events.length} of {data.total} events
        </div>
      )}
    </div>
  );
}

