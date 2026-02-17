import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { createOverride, deleteOverride, getTimeline, listOverrides } from "@/services/api/oncall";
import OverrideModal from "./OverrideModal";
import { useState } from "react";

// DataTable not used: TimelineView renders a visual timeline/Gantt-style layout
// for on-call schedules that doesn't map to standard table rows and columns.

interface TimelineViewProps {
  scheduleId: number;
}

export default function TimelineView({ scheduleId }: TimelineViewProps) {
  const queryClient = useQueryClient();
  const [overrideOpen, setOverrideOpen] = useState(false);
  const timelineQuery = useQuery({
    queryKey: ["oncall-timeline", scheduleId],
    queryFn: () => getTimeline(scheduleId, 14),
  });
  const overridesQuery = useQuery({
    queryKey: ["oncall-overrides", scheduleId],
    queryFn: () => listOverrides(scheduleId),
  });

  return (
    <div className="space-y-3 rounded border border-border p-3">
      <div className="space-y-2">
        {(timelineQuery.data?.slots ?? []).slice(0, 20).map((slot, idx) => (
          <div key={`${slot.start}-${idx}`} className="space-y-1">
            <div className="text-xs text-muted-foreground">
              {new Date(slot.start).toLocaleString()} - {new Date(slot.end).toLocaleString()}
            </div>
            <div
              className={`rounded px-2 py-1 text-xs ${
                slot.is_override ? "bg-amber-500/20 text-amber-700 dark:text-amber-300" : "bg-blue-500/20"
              }`}
            >
              {slot.layer_name}: {slot.responder} {slot.is_override ? "(override)" : ""}
            </div>
          </div>
        ))}
      </div>

      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <div className="text-sm font-medium">Overrides</div>
          <Button size="sm" onClick={() => setOverrideOpen(true)}>
            Add Override
          </Button>
        </div>
        <div className="overflow-x-auto rounded border border-border">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border bg-muted/40">
                <th className="px-2 py-1 text-left">Responder</th>
                <th className="px-2 py-1 text-left">From</th>
                <th className="px-2 py-1 text-left">To</th>
                <th className="px-2 py-1 text-left">Reason</th>
                <th className="px-2 py-1 text-left">Action</th>
              </tr>
            </thead>
            <tbody>
              {(overridesQuery.data?.overrides ?? []).map((override) => (
                <tr key={override.override_id} className="border-b border-border/40">
                  <td className="px-2 py-1">{override.responder}</td>
                  <td className="px-2 py-1">{new Date(override.start_at).toLocaleString()}</td>
                  <td className="px-2 py-1">{new Date(override.end_at).toLocaleString()}</td>
                  <td className="px-2 py-1">{override.reason ?? "-"}</td>
                  <td className="px-2 py-1">
                    <Button
                      variant="destructive"
                      size="sm"
                      onClick={async () => {
                        await deleteOverride(scheduleId, override.override_id);
                        await queryClient.invalidateQueries({ queryKey: ["oncall-overrides", scheduleId] });
                        await queryClient.invalidateQueries({ queryKey: ["oncall-timeline", scheduleId] });
                      }}
                    >
                      Delete
                    </Button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <OverrideModal
        open={overrideOpen}
        onOpenChange={setOverrideOpen}
        onSave={async (payload) => {
          await createOverride(scheduleId, payload);
          await queryClient.invalidateQueries({ queryKey: ["oncall-overrides", scheduleId] });
          await queryClient.invalidateQueries({ queryKey: ["oncall-timeline", scheduleId] });
        }}
      />
    </div>
  );
}
