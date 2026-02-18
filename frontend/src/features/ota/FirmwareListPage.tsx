import { useState } from "react";
import { useCreateFirmware, useFirmwareVersions } from "@/hooks/use-ota";
import { Button } from "@/components/ui/button";
import { PageHeader } from "@/components/shared";
import { DataTable } from "@/components/ui/data-table";
import { type ColumnDef } from "@tanstack/react-table";
import type { FirmwareVersion } from "@/services/api/ota";
import { Plus } from "lucide-react";

function formatFileSize(bytes: number | null): string {
  if (!bytes || bytes <= 0) return "—";
  if (bytes < 1024) return `${bytes} B`;
  const kb = bytes / 1024;
  if (kb < 1024) return `${kb.toFixed(1)} KB`;
  const mb = kb / 1024;
  return `${mb.toFixed(1)} MB`;
}

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

  const columns: ColumnDef<FirmwareVersion>[] = [
    {
      accessorKey: "version",
      header: "Version",
      cell: ({ row }) => (
        <span className="font-mono font-medium">{row.original.version}</span>
      ),
    },
    {
      accessorKey: "description",
      header: "Description",
      cell: ({ row }) => (
        <span className="max-w-[200px] truncate text-sm">
          {row.original.description ?? "—"}
        </span>
      ),
    },
    {
      accessorKey: "device_type",
      header: "Device Type",
      cell: ({ row }) => <span className="text-sm">{row.original.device_type ?? "—"}</span>,
    },
    {
      accessorKey: "file_size_bytes",
      header: "File Size",
      cell: ({ row }) => (
        <span className="text-sm">{formatFileSize(row.original.file_size_bytes)}</span>
      ),
    },
    {
      accessorKey: "checksum_sha256",
      header: "Checksum",
      enableSorting: false,
      cell: ({ row }) => (
        <span className="max-w-[140px] truncate font-mono text-sm text-muted-foreground">
          {row.original.checksum_sha256 ? `${row.original.checksum_sha256.slice(0, 16)}...` : "—"}
        </span>
      ),
    },
    {
      accessorKey: "created_at",
      header: "Created",
      cell: ({ row }) => (
        <span className="text-xs text-muted-foreground">
          {new Date(row.original.created_at).toLocaleDateString()}
        </span>
      ),
    },
  ];

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
    <div className="space-y-4">
      <PageHeader
        title="Firmware Versions"
        description="Registered firmware binaries available for OTA deployment."
        action={
          <Button onClick={() => setShowUpload(true)}>
            <Plus className="mr-1 h-4 w-4" />
            Add Firmware
          </Button>
        }
      />

      <DataTable
        columns={columns}
        data={firmwareVersions}
        isLoading={isLoading}
        emptyState={
          <div className="rounded-lg border border-border py-8 text-center text-muted-foreground">
            No firmware versions registered yet. Upload a firmware version to begin OTA updates.
          </div>
        }
        manualPagination={false}
      />

      {showUpload && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
          <div className="w-full max-w-md rounded-lg border border-border bg-background p-4 shadow-lg space-y-3">
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

