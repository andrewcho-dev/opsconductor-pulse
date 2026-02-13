import { useEffect, useState } from "react";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import type { Device, DeviceUpdate } from "@/services/api/types";
import { geocodeAddress } from "@/services/api/devices";

interface DeviceEditModalProps {
  device: Device;
  open: boolean;
  onSave: (update: DeviceUpdate) => Promise<void>;
  onClose: () => void;
}

export function DeviceEditModal({
  device,
  open,
  onSave,
  onClose,
}: DeviceEditModalProps) {
  const [model, setModel] = useState("");
  const [manufacturer, setManufacturer] = useState("");
  const [serialNumber, setSerialNumber] = useState("");
  const [macAddress, setMacAddress] = useState("");
  const [imei, setImei] = useState("");
  const [iccid, setIccid] = useState("");
  const [hwRevision, setHwRevision] = useState("");
  const [fwVersion, setFwVersion] = useState("");
  const [latitude, setLatitude] = useState(device.latitude?.toString() || "");
  const [longitude, setLongitude] = useState(device.longitude?.toString() || "");
  const [address, setAddress] = useState("");
  const [notes, setNotes] = useState("");
  const [saving, setSaving] = useState(false);
  const [geocoding, setGeocoding] = useState(false);
  const [geocodeError, setGeocodeError] = useState<string | null>(null);

  useEffect(() => {
    if (!open) return;
    setModel(device.model ?? "");
    setManufacturer(device.manufacturer ?? "");
    setSerialNumber(device.serial_number ?? "");
    setMacAddress(device.mac_address ?? "");
    setImei(device.imei ?? "");
    setIccid(device.iccid ?? "");
    setHwRevision(device.hw_revision ?? "");
    setFwVersion(device.fw_version ?? "");
    setLatitude(device.latitude != null ? String(device.latitude) : "");
    setLongitude(device.longitude != null ? String(device.longitude) : "");
    setAddress(device.address ?? "");
    setNotes(device.notes ?? "");
  }, [device, open]);

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    const latValue = latitude.trim();
    const lngValue = longitude.trim();
    const parsedLat = latValue ? Number(latValue) : null;
    const parsedLng = lngValue ? Number(lngValue) : null;
    const hasManualLocation =
      parsedLat != null && !Number.isNaN(parsedLat) && parsedLng != null && !Number.isNaN(parsedLng);
    const update: DeviceUpdate = {
      model: model.trim() || null,
      manufacturer: manufacturer.trim() || null,
      serial_number: serialNumber.trim() || null,
      mac_address: macAddress.trim() || null,
      imei: imei.trim() || null,
      iccid: iccid.trim() || null,
      hw_revision: hwRevision.trim() || null,
      fw_version: fwVersion.trim() || null,
      address: address.trim() || null,
      notes: notes.trim() || null,
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
  }

  async function handleGeocode() {
    if (!address.trim()) return;

    setGeocoding(true);
    setGeocodeError(null);

    try {
      const result = await geocodeAddress(address.trim());

      if (result.error) {
        setGeocodeError(result.error);
      } else if (result.latitude && result.longitude) {
        setLatitude(String(result.latitude));
        setLongitude(String(result.longitude));
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
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Edit Device</DialogTitle>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-3 text-xs">
          <div className="grid grid-cols-2 gap-2">
            <div>
              <label>Model</label>
              <Input
                value={model}
                onChange={(e) => setModel(e.target.value)}
                className="h-7 text-xs"
              />
            </div>
            <div>
              <label>Manufacturer</label>
              <Input
                value={manufacturer}
                onChange={(e) => setManufacturer(e.target.value)}
                className="h-7 text-xs"
              />
            </div>
            <div>
              <label>Serial</label>
              <Input
                value={serialNumber}
                onChange={(e) => setSerialNumber(e.target.value)}
                className="h-7 text-xs"
              />
            </div>
            <div>
              <label>MAC</label>
              <Input
                value={macAddress}
                onChange={(e) => setMacAddress(e.target.value)}
                className="h-7 text-xs"
              />
            </div>
            <div>
              <label>IMEI</label>
              <Input
                value={imei}
                onChange={(e) => setImei(e.target.value)}
                className="h-7 text-xs"
              />
            </div>
            <div>
              <label>SIM/ICCID</label>
              <Input
                value={iccid}
                onChange={(e) => setIccid(e.target.value)}
                className="h-7 text-xs"
              />
            </div>
            <div>
              <label>HW Rev</label>
              <Input
                value={hwRevision}
                onChange={(e) => setHwRevision(e.target.value)}
                className="h-7 text-xs"
              />
            </div>
            <div>
              <label>FW Ver</label>
              <Input
                value={fwVersion}
                onChange={(e) => setFwVersion(e.target.value)}
                className="h-7 text-xs"
              />
            </div>
          </div>

          <div className="border-t pt-2 mt-2">
            <div className="text-xs text-muted-foreground mb-2">
              Location — GPS coordinates preferred (auto-detected from telemetry).
              Address is optional fallback.
            </div>

            <div className="grid grid-cols-2 gap-2 mb-2">
              <div>
                <label className="text-xs text-muted-foreground">Latitude</label>
                <Input
                  type="text"
                  value={latitude}
                  onChange={(e) => setLatitude(e.target.value)}
                  placeholder="e.g. 37.7749"
                  className="h-7 text-xs"
                />
              </div>
              <div>
                <label className="text-xs text-muted-foreground">Longitude</label>
                <Input
                  type="text"
                  value={longitude}
                  onChange={(e) => setLongitude(e.target.value)}
                  placeholder="e.g. -122.4194"
                  className="h-7 text-xs"
                />
              </div>
            </div>

            <div>
              <label className="text-xs text-muted-foreground">
                Street Address (optional, used if no GPS)
              </label>
              <div className="flex gap-1 items-center">
                <Input
                  value={address}
                  onChange={(e) => setAddress(e.target.value)}
                  placeholder="e.g. 123 Main St, City, State"
                  className="h-7 text-xs flex-1"
                />
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  className="h-7 text-xs px-2"
                  onClick={handleGeocode}
                  disabled={!address.trim() || geocoding}
                >
                  {geocoding ? "..." : "Lookup"}
                </Button>
              </div>
              {geocodeError && (
                <div className="text-xs text-destructive">{geocodeError}</div>
              )}
            </div>

            <div className="text-[10px] text-muted-foreground mt-1">
              Note: Manually setting location will prevent auto-updates from telemetry
              GPS data.
            </div>
          </div>

          <div>
            <label>Notes</label>
            <Textarea
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              className="h-16 text-xs"
            />
          </div>

          <div className="flex justify-end gap-2">
            <Button variant="outline" type="button" onClick={onClose}>
              Cancel
            </Button>
            <Button type="submit" disabled={saving}>
              {saving ? "Saving..." : "Save"}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
}
