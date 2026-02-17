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
import { Textarea } from "@/components/ui/textarea";
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import type { Device, DeviceUpdate } from "@/services/api/types";
import { geocodeAddress } from "@/services/api/devices";
import { useFormDirtyGuard } from "@/hooks/use-form-dirty-guard";
import { z } from "zod";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";

interface DeviceEditModalProps {
  device: Device;
  open: boolean;
  onSave: (update: DeviceUpdate) => Promise<void>;
  onClose: () => void;
}

const MAC_REGEX = /^([0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}$/;

const deviceEditSchema = z.object({
  model: z.string().max(100).optional().or(z.literal("")),
  manufacturer: z.string().max(100).optional().or(z.literal("")),
  serial_number: z.string().max(100).optional().or(z.literal("")),
  mac_address: z
    .string()
    .max(100)
    .optional()
    .or(z.literal(""))
    .refine((v) => !v || MAC_REGEX.test(v), "Invalid MAC address format"),
  imei: z.string().max(20).optional().or(z.literal("")),
  iccid: z.string().max(22).optional().or(z.literal("")),
  hw_revision: z.string().max(50).optional().or(z.literal("")),
  fw_version: z.string().max(50).optional().or(z.literal("")),
  latitude: z
    .string()
    .optional()
    .or(z.literal(""))
    .superRefine((v, ctx) => {
      if (!v) return;
      const n = Number(v);
      if (Number.isNaN(n)) {
        ctx.addIssue({ code: "custom", message: "Must be a number" });
        return;
      }
      if (n < -90 || n > 90) ctx.addIssue({ code: "custom", message: "Must be between -90 and 90" });
    }),
  longitude: z
    .string()
    .optional()
    .or(z.literal(""))
    .superRefine((v, ctx) => {
      if (!v) return;
      const n = Number(v);
      if (Number.isNaN(n)) {
        ctx.addIssue({ code: "custom", message: "Must be a number" });
        return;
      }
      if (n < -180 || n > 180) ctx.addIssue({ code: "custom", message: "Must be between -180 and 180" });
    }),
  address: z.string().max(500).optional().or(z.literal("")),
  notes: z.string().max(2000).optional().or(z.literal("")),
});

type DeviceEditFormValues = z.infer<typeof deviceEditSchema>;

export function DeviceEditModal({
  device,
  open,
  onSave,
  onClose,
}: DeviceEditModalProps) {
  const [saving, setSaving] = useState(false);
  const [geocoding, setGeocoding] = useState(false);
  const [geocodeError, setGeocodeError] = useState<string | null>(null);

  const defaults = useMemo<DeviceEditFormValues>(
    () => ({
      model: device.model ?? "",
      manufacturer: device.manufacturer ?? "",
      serial_number: device.serial_number ?? "",
      mac_address: device.mac_address ?? "",
      imei: device.imei ?? "",
      iccid: device.iccid ?? "",
      hw_revision: device.hw_revision ?? "",
      fw_version: device.fw_version ?? "",
      latitude: device.latitude != null ? String(device.latitude) : "",
      longitude: device.longitude != null ? String(device.longitude) : "",
      address: device.address ?? "",
      notes: device.notes ?? "",
    }),
    [device]
  );

  const form = useForm<DeviceEditFormValues>({
    resolver: zodResolver(deviceEditSchema),
    defaultValues: defaults,
  });

  const { handleClose, showConfirm, confirmDiscard, cancelDiscard } = useFormDirtyGuard({
    form,
    onClose,
  });

  useEffect(() => {
    if (!open) return;
    form.reset(defaults);
    setGeocodeError(null);
  }, [defaults, device, form, open]);

  const onSubmit = async (values: DeviceEditFormValues) => {
    const latValue = (values.latitude ?? "").trim();
    const lngValue = (values.longitude ?? "").trim();
    const parsedLat = latValue ? Number(latValue) : null;
    const parsedLng = lngValue ? Number(lngValue) : null;
    const hasManualLocation =
      parsedLat != null &&
      !Number.isNaN(parsedLat) &&
      parsedLng != null &&
      !Number.isNaN(parsedLng);

    const update: DeviceUpdate = {
      model: values.model?.trim() || null,
      manufacturer: values.manufacturer?.trim() || null,
      serial_number: values.serial_number?.trim() || null,
      mac_address: values.mac_address?.trim() || null,
      imei: values.imei?.trim() || null,
      iccid: values.iccid?.trim() || null,
      hw_revision: values.hw_revision?.trim() || null,
      fw_version: values.fw_version?.trim() || null,
      address: values.address?.trim() || null,
      notes: values.notes?.trim() || null,
      latitude: parsedLat != null && !Number.isNaN(parsedLat) ? parsedLat : null,
      longitude: parsedLng != null && !Number.isNaN(parsedLng) ? parsedLng : null,
      location_source: hasManualLocation ? "manual" : undefined,
    };

    setSaving(true);
    try {
      await onSave(update);
      onClose();
    } finally {
      setSaving(false);
    }
  };

  async function handleGeocode() {
    const addr = (form.getValues("address") ?? "").trim();
    if (!addr) return;

    setGeocoding(true);
    setGeocodeError(null);

    try {
      const result = await geocodeAddress(addr);

      if (result.error) {
        setGeocodeError(result.error);
      } else if (result.latitude && result.longitude) {
        form.setValue("latitude", String(result.latitude), { shouldDirty: true });
        form.setValue("longitude", String(result.longitude), { shouldDirty: true });
      } else {
        setGeocodeError("Address not found");
      }
    } catch (err) {
      console.error("Geocoding failed:", err);
      setGeocodeError("Lookup failed");
    }

    setGeocoding(false);
  }

  return (
    <>
      <Dialog
        open={open}
        onOpenChange={(isOpen) => {
          if (!isOpen) handleClose();
        }}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Edit Device</DialogTitle>
          </DialogHeader>
          <Form {...form}>
            <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-3 text-xs">
            <div className="grid grid-cols-2 gap-2">
              <FormField
                control={form.control}
                name="model"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel className="text-xs">Model</FormLabel>
                    <FormControl>
                      <Input {...field} className="h-7 text-xs" />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <FormField
                control={form.control}
                name="manufacturer"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel className="text-xs">Manufacturer</FormLabel>
                    <FormControl>
                      <Input {...field} className="h-7 text-xs" />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <FormField
                control={form.control}
                name="serial_number"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel className="text-xs">Serial</FormLabel>
                    <FormControl>
                      <Input {...field} className="h-7 text-xs" />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <FormField
                control={form.control}
                name="mac_address"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel className="text-xs">MAC</FormLabel>
                    <FormControl>
                      <Input {...field} className="h-7 text-xs" placeholder="AA:BB:CC:DD:EE:FF" />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <FormField
                control={form.control}
                name="imei"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel className="text-xs">IMEI</FormLabel>
                    <FormControl>
                      <Input {...field} className="h-7 text-xs" />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <FormField
                control={form.control}
                name="iccid"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel className="text-xs">SIM/ICCID</FormLabel>
                    <FormControl>
                      <Input {...field} className="h-7 text-xs" />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <FormField
                control={form.control}
                name="hw_revision"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel className="text-xs">HW Rev</FormLabel>
                    <FormControl>
                      <Input {...field} className="h-7 text-xs" />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <FormField
                control={form.control}
                name="fw_version"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel className="text-xs">FW Ver</FormLabel>
                    <FormControl>
                      <Input {...field} className="h-7 text-xs" />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
            </div>

            <div className="border-t pt-2 mt-2">
              <div className="text-xs text-muted-foreground mb-2">
                Location — GPS coordinates preferred (auto-detected from telemetry).
                Address is optional fallback.
              </div>

              <div className="grid grid-cols-2 gap-2 mb-2">
                <FormField
                  control={form.control}
                  name="latitude"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel className="text-xs text-muted-foreground">Latitude</FormLabel>
                      <FormControl>
                        <Input
                          type="text"
                          placeholder="e.g. 37.7749"
                          className="h-7 text-xs"
                          {...field}
                        />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
                <FormField
                  control={form.control}
                  name="longitude"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel className="text-xs text-muted-foreground">Longitude</FormLabel>
                      <FormControl>
                        <Input
                          type="text"
                          placeholder="e.g. -122.4194"
                          className="h-7 text-xs"
                          {...field}
                        />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
              </div>

              <FormField
                control={form.control}
                name="address"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel className="text-xs text-muted-foreground">
                      Street Address (optional, used if no GPS)
                    </FormLabel>
                    <div className="flex gap-1 items-center">
                      <FormControl>
                        <Input
                          {...field}
                          placeholder="e.g. 123 Main St, City, State"
                          className="h-7 text-xs flex-1"
                        />
                      </FormControl>
                      <Button
                        type="button"
                        variant="outline"
                        size="sm"
                        className="h-7 text-xs px-2"
                        onClick={handleGeocode}
                        disabled={!String(field.value ?? "").trim() || geocoding}
                      >
                        {geocoding ? "..." : "Lookup"}
                      </Button>
                    </div>
                    {geocodeError && <div className="text-xs text-destructive">{geocodeError}</div>}
                    <FormMessage />
                  </FormItem>
                )}
              />

              <div className="text-[10px] text-muted-foreground mt-1">
                Note: Manually setting location will prevent auto-updates from telemetry
                GPS data.
              </div>
            </div>

            <FormField
              control={form.control}
              name="notes"
              render={({ field }) => (
                <FormItem>
                  <FormLabel className="text-xs">Notes</FormLabel>
                  <FormControl>
                    <Textarea {...field} className="h-16 text-xs" />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            <div className="flex justify-end gap-2">
              <Button variant="outline" type="button" onClick={handleClose}>
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
