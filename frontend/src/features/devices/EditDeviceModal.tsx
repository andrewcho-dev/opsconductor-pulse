import { useMemo, useState } from "react";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import type { Device } from "@/services/api/types";
import { updateDevice } from "@/services/api/devices";

interface EditDeviceModalProps {
  open: boolean;
  device: Device | null;
  onClose: () => void;
  onSaved: () => Promise<void>;
}

export function EditDeviceModal({ open, device, onClose, onSaved }: EditDeviceModalProps) {
  const initialName = useMemo(() => device?.model ?? "", [device]);
  const initialSite = useMemo(() => device?.site_id ?? "", [device]);
  const initialTags = useMemo(() => (device?.tags ?? []).join(","), [device]);
  const [name, setName] = useState(initialName);
  const [siteId, setSiteId] = useState(initialSite);
  const [tagsInput, setTagsInput] = useState(initialTags);
  const [saving, setSaving] = useState(false);

  if (!device) return null;

  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    const tags = tagsInput
      .split(",")
      .map((tag) => tag.trim())
      .filter(Boolean);
    setSaving(true);
    try {
      await updateDevice(device.device_id, {
        name,
        site_id: siteId,
        tags,
      });
      await onSaved();
      onClose();
    } finally {
      setSaving(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Edit Device</DialogTitle>
        </DialogHeader>
        <form className="space-y-3" onSubmit={submit}>
          <Input value={name} onChange={(e) => setName(e.target.value)} placeholder="Device Name" />
          <Input value={siteId} onChange={(e) => setSiteId(e.target.value)} placeholder="Site" />
          <Input value={tagsInput} onChange={(e) => setTagsInput(e.target.value)} placeholder="Tags (comma separated)" />
          <div className="flex justify-end gap-2">
            <Button type="button" variant="outline" onClick={onClose}>Cancel</Button>
            <Button type="submit" disabled={saving}>{saving ? "Saving..." : "Save"}</Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
}
