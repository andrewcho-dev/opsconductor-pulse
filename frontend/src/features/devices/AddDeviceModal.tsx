import { useState } from "react";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { provisionDevice, type ProvisionDeviceResponse } from "@/services/api/devices";
import { CredentialModal } from "./CredentialModal";
import { z } from "zod";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import {
  Form,
  FormField,
  FormItem,
  FormLabel,
  FormControl,
  FormMessage,
} from "@/components/ui/form";

const addDeviceSchema = z.object({
  name: z.string().min(1, "Device name is required").max(100),
  deviceType: z.string().min(1, "Device type is required").max(50),
  siteId: z.string().optional(),
  tags: z.string().optional(),
});

type AddDeviceFormValues = z.infer<typeof addDeviceSchema>;

interface AddDeviceModalProps {
  open: boolean;
  onClose: () => void;
  onCreated: () => Promise<void>;
}

export function AddDeviceModal({ open, onClose, onCreated }: AddDeviceModalProps) {
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [credentials, setCredentials] = useState<ProvisionDeviceResponse | null>(null);

  const form = useForm<AddDeviceFormValues>({
    resolver: zodResolver(addDeviceSchema),
    defaultValues: { name: "", deviceType: "", siteId: "", tags: "" },
  });

  const reset = () => {
    form.reset();
    setError(null);
  };

  const closeAll = () => {
    reset();
    setCredentials(null);
    onClose();
  };

  const submit = async (values: AddDeviceFormValues) => {
    setSaving(true);
    setError(null);
    try {
      const tags = (values.tags ?? "")
        .split(",")
        .map((tag) => tag.trim())
        .filter(Boolean);
      const result = await provisionDevice({
        name: values.name.trim(),
        device_type: values.deviceType.trim(),
        site_id: values.siteId?.trim() || undefined,
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
          <Form {...form}>
            <form className="space-y-3" onSubmit={form.handleSubmit(submit)}>
              <FormField
                control={form.control}
                name="name"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Device Name *</FormLabel>
                    <FormControl>
                      <Input placeholder="Device Name" {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <FormField
                control={form.control}
                name="deviceType"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Device Type *</FormLabel>
                    <FormControl>
                      <Input placeholder="Device Type" {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <FormField
                control={form.control}
                name="siteId"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Site</FormLabel>
                    <FormControl>
                      <Input placeholder="Site (optional)" {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <FormField
                control={form.control}
                name="tags"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Tags</FormLabel>
                    <FormControl>
                      <Input placeholder="Tags (comma separated)" {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              {error && <div className="text-xs text-destructive">{error}</div>}
              <div className="flex justify-end gap-2">
                <Button type="button" variant="outline" onClick={closeAll}>
                  Cancel
                </Button>
                <Button type="submit" disabled={saving}>
                  {saving ? "Creating..." : "Create"}
                </Button>
              </div>
            </form>
          </Form>
        </DialogContent>
      </Dialog>
      <CredentialModal
        open={Boolean(credentials)}
        credentials={credentials}
        deviceName={form.getValues("name")}
        onClose={closeAll}
      />
    </>
  );
}
