import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";

interface OverrideModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSave: (payload: {
    responder: string;
    start_at: string;
    end_at: string;
    reason?: string;
  }) => Promise<void>;
}

export default function OverrideModal({ open, onOpenChange, onSave }: OverrideModalProps) {
  const [responder, setResponder] = useState("");
  const [startAt, setStartAt] = useState("");
  const [endAt, setEndAt] = useState("");
  const [reason, setReason] = useState("");
  const [saving, setSaving] = useState(false);

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Add Override</DialogTitle>
        </DialogHeader>
        <div className="space-y-3">
          <Input placeholder="Who covers" value={responder} onChange={(e) => setResponder(e.target.value)} />
          <Input type="datetime-local" value={startAt} onChange={(e) => setStartAt(e.target.value)} />
          <Input type="datetime-local" value={endAt} onChange={(e) => setEndAt(e.target.value)} />
          <Input placeholder="Reason (optional)" value={reason} onChange={(e) => setReason(e.target.value)} />
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)} disabled={saving}>
            Cancel
          </Button>
          <Button
            disabled={saving || !responder || !startAt || !endAt}
            onClick={async () => {
              setSaving(true);
              try {
                await onSave({
                  responder,
                  start_at: new Date(startAt).toISOString(),
                  end_at: new Date(endAt).toISOString(),
                  reason: reason || undefined,
                });
                onOpenChange(false);
                setResponder("");
                setStartAt("");
                setEndAt("");
                setReason("");
              } finally {
                setSaving(false);
              }
            }}
          >
            {saving ? "Saving..." : "Save"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
