import { useState } from "react";
import { useCreateFirmware, useFirmwareVersions } from "@/hooks/use-ota";
import { Button } from "@/components/ui/button";
import { PageHeader } from "@/components/shared";

export default function FirmwareListPage() {
  const { data, isLoading } = useFirmwareVersions();
  const createMut = useCreateFirmware();
  const [showUpload, setShowUpload] = useState(false);
  const [version, setVersion] = useState("");
  const [description, setDescription] = useState("");
  const [fileUrl, setFileUrl] = useState("");
  const [deviceType, setDeviceType] = useState("");
  const [fileSize, setFileSize] = useState("");
  const [checksum, setChecksum] = useState("");

  const firmwareVersions = data?.firmware_versions ?? [];

  async function handleCreate() {
    try {
      await createMut.mutateAsync({
        version: version.trim(),
        description: description.trim() || undefined,
        file_url: fileUrl.trim(),
        device_type: deviceType.trim() || undefined,
        file_size_bytes: fileSize ? Number(fileSize) : undefined,
        checksum_sha256: checksum.trim() || undefined,
      });
      setShowUpload(false);
      setVersion("");
      setDescription("");
      setFileUrl("");
      setDeviceType("");
      setFileSize("");
      setChecksum("");
    } catch (err) {
      console.error("Failed to create firmware:", err);
    }
  }

  return (
    <div className="p-4 space-y-4">
      <PageHeader
        title="Firmware Versions"
        description="Registered firmware binaries available for OTA deployment."
        action={<Button onClick={() => setShowUpload(true)}>+ Register Firmware</Button>}
      />

      {isLoading && (
        <div className="text-sm text-muted-foreground">
          Loading firmware versions...
        </div>
      )}

      <div className="rounded border border-border overflow-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-border bg-muted/40">
              {["Version", "Description", "Device Type", "File Size", "Checksum", "Created"].map(
                (h) => (
                  <th key={h} className="px-3 py-2 text-left font-medium">
                    {h}
                  </th>
                )
              )}
            </tr>
          </thead>
          <tbody>
            {firmwareVersions.map((fw) => (
              <tr key={fw.id} className="border-b border-border/40 hover:bg-muted/30">
                <td className="px-3 py-2 font-mono font-medium">{fw.version}</td>
                <td className="px-3 py-2 text-xs max-w-[200px] truncate">
                  {fw.description ?? "-"}
                </td>
                <td className="px-3 py-2 text-xs">{fw.device_type ?? "All"}</td>
                <td className="px-3 py-2 text-xs">
                  {fw.file_size_bytes
                    ? `${(fw.file_size_bytes / 1024 / 1024).toFixed(1)} MB`
                    : "-"}
                </td>
                <td className="px-3 py-2 text-xs font-mono max-w-[120px] truncate">
                  {fw.checksum_sha256 ? fw.checksum_sha256.slice(0, 16) + "..." : "-"}
                </td>
                <td className="px-3 py-2 text-xs">
                  {new Date(fw.created_at).toLocaleDateString()}
                </td>
              </tr>
            ))}
            {firmwareVersions.length === 0 && !isLoading && (
              <tr>
                <td colSpan={6} className="px-3 py-6 text-center text-sm text-muted-foreground">
                  No firmware versions registered yet.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {showUpload && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
          <div className="w-full max-w-md rounded-lg border border-border bg-background p-6 shadow-lg space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-lg font-semibold">Register Firmware Version</h3>
              <Button variant="ghost" size="sm" onClick={() => setShowUpload(false)}>
                X
              </Button>
            </div>
            <div className="space-y-3">
              <div>
                <label className="text-sm font-medium">Version *</label>
                <input
                  type="text"
                  value={version}
                  onChange={(e) => setVersion(e.target.value)}
                  placeholder="e.g., 2.1.0"
                  className="mt-1 w-full rounded border border-border bg-background px-3 py-2 text-sm"
                />
              </div>
              <div>
                <label className="text-sm font-medium">File URL *</label>
                <input
                  type="text"
                  value={fileUrl}
                  onChange={(e) => setFileUrl(e.target.value)}
                  placeholder="https://firmware-bucket.s3.amazonaws.com/fw-2.1.0.bin"
                  className="mt-1 w-full rounded border border-border bg-background px-3 py-2 text-sm"
                />
              </div>
              <div>
                <label className="text-sm font-medium">Description</label>
                <input
                  type="text"
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  placeholder="Bug fixes and performance improvements"
                  className="mt-1 w-full rounded border border-border bg-background px-3 py-2 text-sm"
                />
              </div>
              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="text-sm font-medium">Device Type</label>
                  <input
                    type="text"
                    value={deviceType}
                    onChange={(e) => setDeviceType(e.target.value)}
                    placeholder="sensor-v2"
                    className="mt-1 w-full rounded border border-border bg-background px-3 py-2 text-sm"
                  />
                </div>
                <div>
                  <label className="text-sm font-medium">File Size (bytes)</label>
                  <input
                    type="number"
                    value={fileSize}
                    onChange={(e) => setFileSize(e.target.value)}
                    placeholder="1048576"
                    className="mt-1 w-full rounded border border-border bg-background px-3 py-2 text-sm"
                  />
                </div>
              </div>
              <div>
                <label className="text-sm font-medium">SHA-256 Checksum</label>
                <input
                  type="text"
                  value={checksum}
                  onChange={(e) => setChecksum(e.target.value)}
                  placeholder="abc123..."
                  className="mt-1 w-full rounded border border-border bg-background px-3 py-2 text-sm"
                />
              </div>
            </div>
            <div className="flex justify-end gap-2">
              <Button variant="outline" onClick={() => setShowUpload(false)}>
                Cancel
              </Button>
              <Button
                onClick={() => void handleCreate()}
                disabled={!version.trim() || !fileUrl.trim() || createMut.isPending}
              >
                {createMut.isPending ? "Registering..." : "Register"}
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

