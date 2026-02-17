import { useState } from "react";
import { Pencil } from "lucide-react";
import { StatusBadge } from "@/components/shared";
import { Skeleton } from "@/components/ui/skeleton";
import type { Device } from "@/services/api/types";
import { formatTimestamp } from "@/lib/format";

interface DeviceInfoCardProps {
  device: Device | undefined;
  isLoading: boolean;
  tags: string[];
  onTagsChange: (tags: string[]) => void;
  notesValue: string;
  onNotesChange: (value: string) => void;
  onNotesBlur?: () => void;
  onEdit: () => void;
}

export function DeviceInfoCard({
  device,
  isLoading,
  tags,
  onTagsChange,
  notesValue,
  onNotesChange,
  onNotesBlur,
  onEdit,
}: DeviceInfoCardProps) {
  const [tagInput, setTagInput] = useState("");
  if (isLoading) {
    return (
      <div className="border rounded p-3 bg-card text-sm space-y-1">
        <Skeleton className="h-3 w-64" />
        <Skeleton className="h-3 w-72" />
        <Skeleton className="h-3 w-56" />
      </div>
    );
  }

  if (!device) {
    return (
      <div className="border rounded p-3 bg-card text-sm space-y-1">
        <p className="text-sm text-muted-foreground">Device not found.</p>
      </div>
    );
  }

  return (
    <div className="border rounded p-2 bg-card text-sm">
      <div className="flex items-center gap-3 mb-1">
        <span className="font-mono font-semibold text-sm">
          {device.device_id}
        </span>
        <StatusBadge status={device.status} />
        <span className="text-muted-foreground">Site: {device.site_id}</span>
        <span className="text-muted-foreground">
          {formatTimestamp(device.last_seen_at)}
        </span>
        <button
          type="button"
          onClick={onEdit}
          className="ml-auto text-muted-foreground hover:text-foreground"
          aria-label="Edit device"
        >
          <Pencil className="h-3 w-3" />
        </button>
      </div>

      <div className="grid grid-cols-4 gap-x-3 gap-y-0.5 text-sm">
        <div>
          <span className="text-muted-foreground">Model:</span>{" "}
          {device.model || "—"}
        </div>
        <div>
          <span className="text-muted-foreground">Mfr:</span>{" "}
          {device.manufacturer || "—"}
        </div>
        <div>
          <span className="text-muted-foreground">Serial:</span>{" "}
          {device.serial_number || "—"}
        </div>
        <div>
          <span className="text-muted-foreground">MAC:</span>{" "}
          {device.mac_address || "—"}
        </div>
        <div>
          <span className="text-muted-foreground">IMEI:</span>{" "}
          {device.imei || "—"}
        </div>
        <div>
          <span className="text-muted-foreground">SIM:</span>{" "}
          {device.iccid || "—"}
        </div>
        <div>
          <span className="text-muted-foreground">HW:</span>{" "}
          {device.hw_revision || "—"}
        </div>
        <div>
          <span className="text-muted-foreground">FW:</span>{" "}
          {device.fw_version || "—"}
        </div>
      </div>

      <div className="mt-1 flex items-center gap-1 text-sm">
        <span className="text-muted-foreground">Location:</span>
        {device.latitude != null && device.longitude != null ? (
          <>
            <span>
              {device.latitude.toFixed(6)}, {device.longitude.toFixed(6)}
            </span>
            {device.address && (
              <span className="text-muted-foreground">({device.address})</span>
            )}
            <span className="text-muted-foreground text-sm">
              [{device.location_source || "auto"}]
            </span>
          </>
        ) : device.address ? (
          <>
            <span>{device.address}</span>
            <span className="text-muted-foreground text-sm">[manual]</span>
          </>
        ) : (
          <span className="text-muted-foreground">—</span>
        )}
      </div>

      <div className="mt-1 flex items-center gap-1 text-sm">
        <span className="text-muted-foreground">Tags:</span>
        {tags.map((tag) => (
          <span
            key={tag}
              className="bg-muted px-1 py-0 rounded text-sm inline-flex items-center"
          >
            {tag}
            <button
              type="button"
              onClick={() => onTagsChange(tags.filter((t) => t !== tag))}
              className="ml-0.5 text-muted-foreground hover:text-foreground"
              aria-label={`Remove tag ${tag}`}
            >
              ×
            </button>
          </span>
        ))}
        <input
          type="text"
          placeholder="+"
          value={tagInput}
          onChange={(e) => setTagInput(e.target.value)}
          className="w-12 text-sm bg-transparent border-b border-border py-0 px-0"
          aria-label="Add device tag"
          onKeyDown={(e) => {
            if (e.key === "Enter") {
              e.preventDefault();
              const next = tagInput.trim();
              if (!next) return;
              if (tags.some((t) => t.toLowerCase() === next.toLowerCase())) {
                setTagInput("");
                return;
              }
              onTagsChange([...tags, next]);
              setTagInput("");
            } else if (e.key === "Backspace" && !tagInput && tags.length > 0) {
              onTagsChange(tags.slice(0, -1));
            }
          }}
        />
      </div>

      <div className="mt-1 flex items-center gap-1 text-sm">
        <span className="text-muted-foreground">Notes:</span>
        <input
          type="text"
          value={notesValue}
          onChange={(e) => onNotesChange(e.target.value)}
          onBlur={onNotesBlur}
          className="flex-1 text-sm bg-transparent border-b border-border py-0"
          placeholder="—"
        />
      </div>
    </div>
  );
}
