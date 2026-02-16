import { useEffect, useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  getDeviceTwin,
  type TwinDocument,
  type StructuredDelta,
  updateDesiredState,
  ConflictError,
} from "@/services/api/devices";

interface DeviceTwinPanelProps {
  deviceId: string;
}

const STATUS_BADGE: Record<TwinDocument["sync_status"], string> = {
  synced: "default",
  pending: "secondary",
  stale: "outline",
};

function DeltaDiffView({ delta }: { delta: StructuredDelta }) {
  const hasChanges =
    Object.keys(delta.added).length > 0 ||
    Object.keys(delta.removed).length > 0 ||
    Object.keys(delta.changed).length > 0;

  if (!hasChanges) {
    return (
      <div className="rounded border border-green-300 bg-green-50 px-2 py-1 text-xs text-green-800">
        Twin is in sync ({delta.unchanged_count} key
        {delta.unchanged_count !== 1 ? "s" : ""} matching)
      </div>
    );
  }

  return (
    <div className="space-y-2">
      {Object.keys(delta.added).length > 0 && (
        <div className="rounded border border-green-300 bg-green-50 p-2">
          <div className="mb-1 text-xs font-semibold text-green-800">
            Added ({Object.keys(delta.added).length})
          </div>
          {Object.entries(delta.added).map(([key, value]) => (
            <div key={key} className="flex items-center gap-2 text-xs text-green-900">
              <span className="font-mono font-medium">{key}</span>
              <span className="text-green-600">{JSON.stringify(value)}</span>
            </div>
          ))}
        </div>
      )}

      {Object.keys(delta.removed).length > 0 && (
        <div className="rounded border border-red-300 bg-red-50 p-2">
          <div className="mb-1 text-xs font-semibold text-red-800">
            Removed ({Object.keys(delta.removed).length})
          </div>
          {Object.entries(delta.removed).map(([key, value]) => (
            <div key={key} className="flex items-center gap-2 text-xs text-red-900">
              <span className="font-mono font-medium">{key}</span>
              <span className="text-red-600 line-through">{JSON.stringify(value)}</span>
            </div>
          ))}
        </div>
      )}

      {Object.keys(delta.changed).length > 0 && (
        <div className="rounded border border-amber-300 bg-amber-50 p-2">
          <div className="mb-1 text-xs font-semibold text-amber-800">
            Changed ({Object.keys(delta.changed).length})
          </div>
          {Object.entries(delta.changed).map(([key, change]) => {
            const typed = change as { old_value: unknown; new_value: unknown };
            return (
              <div key={key} className="flex items-center gap-2 text-xs text-amber-900">
                <span className="font-mono font-medium">{key}</span>
                <span className="text-red-600 line-through">
                  {JSON.stringify(typed.old_value)}
                </span>
                <span className="text-muted-foreground">&rarr;</span>
                <span className="text-green-700">{JSON.stringify(typed.new_value)}</span>
              </div>
            );
          })}
        </div>
      )}

      {delta.unchanged_count > 0 && (
        <div className="text-xs text-muted-foreground">
          {delta.unchanged_count} key{delta.unchanged_count !== 1 ? "s" : ""} unchanged
        </div>
      )}
    </div>
  );
}

export function DeviceTwinPanel({ deviceId }: DeviceTwinPanelProps) {
  const [twin, setTwin] = useState<TwinDocument | null>(null);
  const [etag, setEtag] = useState<string>("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [editing, setEditing] = useState(false);
  const [saving, setSaving] = useState(false);
  const [desiredDraft, setDesiredDraft] = useState("{}");

  const loadTwin = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await getDeviceTwin(deviceId);
      setTwin(data);
      setEtag(data.etag);
      setDesiredDraft(JSON.stringify(data.desired, null, 2));
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to load twin";
      setError(message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void loadTwin();
  }, [deviceId]);

  const handleSave = async () => {
    setSaving(true);
    setError(null);
    try {
      const parsed = JSON.parse(desiredDraft) as Record<string, unknown>;
      await updateDesiredState(deviceId, parsed, etag);
      setEditing(false);
      await loadTwin();
    } catch (err) {
      if (err instanceof ConflictError) {
        setError("Another user modified this twin. Refresh to see latest.");
        await loadTwin();
        return;
      }
      const message = err instanceof Error ? err.message : "Failed to save desired state";
      setError(message);
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return <div className="rounded border border-border p-3 text-sm text-muted-foreground">Loading twin...</div>;
  }
  if (!twin) {
    return <div className="rounded border border-border p-3 text-sm text-muted-foreground">No twin data.</div>;
  }

  const deltaKeys = Object.keys(twin.delta);

  return (
    <div className="rounded border border-border p-3 space-y-3">
      <div className="flex flex-wrap items-center gap-2">
        <h4 className="text-sm font-semibold">Device Twin</h4>
        <Badge variant={STATUS_BADGE[twin.sync_status] as "default" | "secondary" | "outline"}>
          {twin.sync_status}
        </Badge>
        <span className="text-xs text-muted-foreground">
          Desired v{twin.desired_version} / Reported v{twin.reported_version}
        </span>
        <Button size="sm" variant="outline" className="ml-auto" onClick={() => void loadTwin()}>
          Refresh
        </Button>
      </div>

      {twin.structured_delta ? (
        <DeltaDiffView delta={twin.structured_delta} />
      ) : (
        deltaKeys.length > 0 && (
          <div className="rounded border border-amber-300 bg-amber-50 px-2 py-1 text-xs text-amber-900">
            Out of sync: {deltaKeys.join(", ")}
          </div>
        )
      )}

      <div className="grid gap-3 md:grid-cols-2">
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <strong className="text-sm">Desired</strong>
            {!editing && (
              <Button size="sm" variant="outline" onClick={() => setEditing(true)}>
                Edit
              </Button>
            )}
          </div>
          {editing ? (
            <div className="space-y-2">
              <textarea
                className="w-full rounded border border-border bg-background p-2 font-mono text-xs"
                rows={12}
                value={desiredDraft}
                onChange={(event) => setDesiredDraft(event.target.value)}
              />
              <div className="flex gap-2">
                <Button size="sm" onClick={() => void handleSave()} disabled={saving}>
                  {saving ? "Saving..." : "Save"}
                </Button>
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => {
                    setEditing(false);
                    setDesiredDraft(JSON.stringify(twin.desired, null, 2));
                    setError(null);
                  }}
                >
                  Cancel
                </Button>
              </div>
            </div>
          ) : (
            <pre className="max-h-72 overflow-auto rounded bg-muted p-2 text-xs">
              {JSON.stringify(twin.desired, null, 2)}
            </pre>
          )}
        </div>
        <div className="space-y-2">
          <strong className="text-sm">Reported</strong>
          <pre className="max-h-72 overflow-auto rounded bg-muted p-2 text-xs">
            {JSON.stringify(twin.reported, null, 2)}
          </pre>
        </div>
      </div>

      {error && <div className="text-xs text-destructive">{error}</div>}

      <div className="text-xs text-muted-foreground">Last updated: {twin.shadow_updated_at ?? "never"}</div>
    </div>
  );
}
