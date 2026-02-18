import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { PageHeader } from "@/components/shared";
import { Button } from "@/components/ui/button";
import { toast } from "sonner";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import {
  createSchedule,
  deleteSchedule,
  getCurrentOncall,
  listSchedules,
  updateSchedule,
  type OncallSchedule,
} from "@/services/api/oncall";
import ScheduleModal from "./ScheduleModal";
import TimelineView from "./TimelineView";
import { getErrorMessage } from "@/lib/errors";

function ScheduleCard({ schedule }: { schedule: OncallSchedule }) {
  const [open, setOpen] = useState(false);
  const currentQuery = useQuery({
    queryKey: ["oncall-current", schedule.schedule_id],
    queryFn: () => getCurrentOncall(schedule.schedule_id),
    refetchInterval: 60000,
  });
  return (
    <div className="rounded border border-border p-3">
      <div className="flex items-center justify-between">
        <div>
          <div className="font-medium">{schedule.name}</div>
          <div className="text-xs text-muted-foreground">Timezone: {schedule.timezone}</div>
          <div className="text-xs">
            Now on-call: {currentQuery.data?.responder || "-"} ({currentQuery.data?.layer || "-"})
          </div>
        </div>
        <Button variant="outline" size="sm" onClick={() => setOpen((v) => !v)}>
          {open ? "Hide" : "View"}
        </Button>
      </div>
      {open && <TimelineView scheduleId={schedule.schedule_id} />}
    </div>
  );
}

export default function OncallSchedulesPage() {
  const queryClient = useQueryClient();
  const [modalOpen, setModalOpen] = useState(false);
  const [editing, setEditing] = useState<OncallSchedule | null>(null);
  const [confirmDeleteSchedule, setConfirmDeleteSchedule] = useState<number | null>(null);
  const schedulesQuery = useQuery({
    queryKey: ["oncall-schedules"],
    queryFn: listSchedules,
  });

  const createMutation = useMutation({
    mutationFn: createSchedule,
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["oncall-schedules"] });
      toast.success("On-call schedule created");
    },
    onError: (err: Error) => {
      toast.error(getErrorMessage(err) || "Failed to create schedule");
    },
  });
  const updateMutation = useMutation({
    mutationFn: ({ id, body }: { id: number; body: Partial<OncallSchedule> }) => updateSchedule(id, body),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["oncall-schedules"] });
      toast.success("On-call schedule updated");
    },
    onError: (err: Error) => {
      toast.error(getErrorMessage(err) || "Failed to update schedule");
    },
  });
  const deleteMutation = useMutation({
    mutationFn: deleteSchedule,
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["oncall-schedules"] });
      toast.success("On-call schedule deleted");
    },
    onError: (err: Error) => {
      toast.error(getErrorMessage(err) || "Failed to delete schedule");
    },
  });

  const schedules = schedulesQuery.data?.schedules ?? [];

  return (
    <div className="space-y-4">
      <PageHeader
        title="On-Call Schedules"
        description="Configure rotation layers and temporary overrides."
        action={
          <Button
            onClick={() => {
              setEditing(null);
              setModalOpen(true);
            }}
          >
            New Schedule
          </Button>
        }
      />

      <div className="space-y-3">
        {schedules.map((schedule) => (
          <div key={schedule.schedule_id} className="space-y-2">
            <div className="flex justify-end gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => {
                  setEditing(schedule);
                  setModalOpen(true);
                }}
              >
                Edit
              </Button>
              <Button
                variant="destructive"
                size="sm"
                onClick={() => setConfirmDeleteSchedule(schedule.schedule_id)}
              >
                Delete
              </Button>
            </div>
            <ScheduleCard schedule={schedule} />
          </div>
        ))}
      </div>

      <ScheduleModal
        open={modalOpen}
        onOpenChange={setModalOpen}
        initial={editing}
        onSave={async (payload) => {
          if (editing) {
            await updateMutation.mutateAsync({ id: editing.schedule_id, body: payload });
          } else {
            await createMutation.mutateAsync(payload);
          }
        }}
      />

      <AlertDialog
        open={!!confirmDeleteSchedule}
        onOpenChange={(open) => !open && setConfirmDeleteSchedule(null)}
      >
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete Schedule</AlertDialogTitle>
            <AlertDialogDescription>
              Are you sure you want to delete this schedule? This cannot be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={async () => {
                if (confirmDeleteSchedule) await deleteMutation.mutateAsync(confirmDeleteSchedule);
                setConfirmDeleteSchedule(null);
              }}
            >
              Delete
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
