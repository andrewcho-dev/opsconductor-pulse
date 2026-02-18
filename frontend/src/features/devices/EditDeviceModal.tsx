import { useEffect, useMemo, useState } from "react";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
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
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import type { Device } from "@/services/api/types";
import { updateDevice } from "@/services/api/devices";
import { useFormDirtyGuard } from "@/hooks/use-form-dirty-guard";
import { z } from "zod";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";

interface EditDeviceModalProps {
  open: boolean;
  device: Device | null;
  onClose: () => void;
  onSaved: () => Promise<void>;
}

const editDeviceSchema = z.object({
  name: z.string().min(1, "Device name is required").max(100),
  site_id: z.string().max(100).optional().or(z.literal("")),
  tags: z.string().max(1000).optional().or(z.literal("")),
});

type EditDeviceFormValues = z.infer<typeof editDeviceSchema>;

export function EditDeviceModal({ open, device, onClose, onSaved }: EditDeviceModalProps) {
  const [saving, setSaving] = useState(false);

  if (!device) return null;

  const defaults = useMemo<EditDeviceFormValues>(
    () => ({
      // Keep existing semantics: this modal edits "name" but was seeded from device.model.
      name: device.model ?? "",
      site_id: device.site_id ?? "",
      tags: (device.tags ?? []).join(","),
    }),
    [device]
  );

  const form = useForm<EditDeviceFormValues>({
    resolver: zodResolver(editDeviceSchema),
    defaultValues: defaults,
  });

  const { handleClose, showConfirm, confirmDiscard, cancelDiscard } = useFormDirtyGuard({
    form,
    onClose,
  });

  useEffect(() => {
    if (!open) return;
    form.reset(defaults);
  }, [defaults, form, open]);

  const onSubmit = async (values: EditDeviceFormValues) => {
    const tags = (values.tags ?? "")
      .split(",")
      .map((tag) => tag.trim())
      .filter(Boolean);
    setSaving(true);
    try {
      await updateDevice(device.device_id, {
        name: values.name,
        site_id: values.site_id ?? "",
        tags,
      });
      await onSaved();
      onClose();
    } finally {
      setSaving(false);
    }
  };

  return (
    <>
      <Dialog
        open={open}
        onOpenChange={(openState) => {
          if (!openState) handleClose();
        }}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Edit Device</DialogTitle>
          </DialogHeader>
          <Form {...form}>
            <form className="space-y-3" onSubmit={form.handleSubmit(onSubmit)}>
            <FormField
              control={form.control}
              name="name"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Device Name</FormLabel>
                  <FormControl>
                    <Input placeholder="Device Name" {...field} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
            <FormField
              control={form.control}
              name="site_id"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Site</FormLabel>
                  <FormControl>
                    <Input placeholder="Site" {...field} />
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
            <div className="flex justify-end gap-2">
              <Button type="button" variant="outline" onClick={handleClose}>
                Cancel
              </Button>
              <Button type="submit" disabled={saving}>
                {saving ? "Saving..." : "Save"}
              </Button>
            </div>
            </form>
          </Form>
        </DialogContent>
      </Dialog>

      <AlertDialog open={showConfirm} onOpenChange={cancelDiscard}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Discard changes?</AlertDialogTitle>
            <AlertDialogDescription>
              You have unsaved changes. Are you sure you want to close without saving?
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel onClick={cancelDiscard}>Keep Editing</AlertDialogCancel>
            <AlertDialogAction
              onClick={confirmDiscard}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              Discard
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  );
}
