import { useState } from "react";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { provisionDevice, type ProvisionDeviceResponse } from "@/services/api/devices";
import { CredentialModal } from "./CredentialModal";

interface AddDeviceModalProps {
  open: boolean;
  onClose: () => void;
  onCreated: () => Promise<void>;
}

export function AddDeviceModal({ open, onClose, onCreated }: AddDeviceModalProps) {
  const [name, setName] = useState("");
  const [deviceType, setDeviceType] = useState("");
  const [siteId, setSiteId] = useState("");
  const [tagsInput, setTagsInput] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [credentials, setCredentials] = useState<ProvisionDeviceResponse | null>(null);

  const reset = () => {
    setName("");
    setDeviceType("");
    setSiteId("");
    setTagsInput("");
    setError(null);
  };

  const closeAll = () => {
    reset();
    setCredentials(null);
    onClose();
  };

  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    setSaving(true);
    setError(null);
    try {
      const tags = tagsInput
        .split(",")
        .map((tag) => tag.trim())
        .filter(Boolean);
      const result = await provisionDevice({
        name: name.trim(),
        device_type: deviceType.trim(),
        site_id: siteId.trim() || undefined,
        tags: tags.length > 0 ? tags : undefined,
      });
      await onCreated();
      setCredentials(result);
    } catch (err) {
      setError((err as Error)?.message ?? "Failed to provision device");
    } finally {
      setSaving(false);
    }
  };

  return (
    <>
      <Dialog open={open && !credentials} onOpenChange={closeAll}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Add Device</DialogTitle>
          </DialogHeader>
          <form className="space-y-3" onSubmit={submit}>
            <Input placeholder="Device Name" value={name} onChange={(e) => setName(e.target.value)} required />
            <Input placeholder="Device Type" value={deviceType} onChange={(e) => setDeviceType(e.target.value)} required />
            <Input placeholder="Site (optional)" value={siteId} onChange={(e) => setSiteId(e.target.value)} />
            <Input placeholder="Tags (comma separated)" value={tagsInput} onChange={(e) => setTagsInput(e.target.value)} />
            {error && <div className="text-xs text-destructive">{error}</div>}
            <div className="flex justify-end gap-2">
              <Button type="button" variant="outline" onClick={closeAll}>Cancel</Button>
              <Button type="submit" disabled={saving}>{saving ? "Creating..." : "Create"}</Button>
            </div>
          </form>
        </DialogContent>
      </Dialog>
      <CredentialModal
        open={Boolean(credentials)}
        credentials={credentials}
        deviceName={name}
        onClose={closeAll}
      />
    </>
  );
}
